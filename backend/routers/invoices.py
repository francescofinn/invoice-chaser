from decimal import Decimal
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from constants import DEFAULT_CURRENCY, INITIAL_FOLLOW_UP_DAY, INVOICE_STATUS_DRAFT, INVOICE_STATUS_SENT, INVOICE_STATUS_VIEWED
from database import get_db, settings
from models import Client, EmailLog, Invoice
from schemas import InvoiceCreate, InvoiceResponse, InvoiceUpdate, PublicInvoiceResponse
from services.email import send_invoice_email
from utils import (
    build_payment_link,
    calculate_invoice_total,
    decimal_to_cents,
    serialize_line_items,
    validate_invoice_status,
)

stripe.api_key = settings.stripe_secret_key

router = APIRouter()


def _load_invoice(
    db: Session,
    invoice_id: int,
    *,
    include_payments: bool = False,
    include_email_logs: bool = False,
) -> Invoice | None:
    options = [joinedload(Invoice.client)]
    if include_payments:
        options.append(joinedload(Invoice.payments))
    if include_email_logs:
        options.append(joinedload(Invoice.email_logs))

    statement = select(Invoice).options(*options).where(Invoice.id == invoice_id)
    return db.scalars(statement).unique().one_or_none()


def _load_invoice_or_404(db: Session, invoice_id: int, **kwargs) -> Invoice:
    invoice = _load_invoice(db, invoice_id, **kwargs)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _load_invoice_by_token_or_404(db: Session, token: UUID) -> Invoice:
    statement = (
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.payments))
        .where(Invoice.token == token)
    )
    invoice = db.scalars(statement).unique().one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _ensure_client_exists(db: Session, client_id: int) -> None:
    if not db.get(Client, client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")


def _create_payment_intent(invoice: Invoice, amount: Decimal) -> dict:
    return stripe.PaymentIntent.create(
        amount=decimal_to_cents(amount),
        currency=DEFAULT_CURRENCY,
        metadata={"invoice_id": str(invoice.id)},
    )


def _compose_initial_email(invoice: Invoice) -> tuple[str, str]:
    total = calculate_invoice_total(invoice.line_items)
    subject = f"Invoice {invoice.invoice_number} from Invoice Chaser"
    body = (
        f"Hi {invoice.client.name},\n\n"
        f"Your invoice {invoice.invoice_number} for ${total} is ready.\n"
        f"Please review and pay by {invoice.due_date.isoformat()}."
    )
    return subject, body


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(status_filter: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db)):
    statement = select(Invoice).options(joinedload(Invoice.client)).order_by(Invoice.id)
    if status_filter is not None:
        try:
            validate_invoice_status(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        statement = statement.where(Invoice.status == status_filter)

    return db.scalars(statement).unique().all()


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    _ensure_client_exists(db, payload.client_id)

    invoice = Invoice(
        client_id=payload.client_id,
        invoice_number=payload.invoice_number,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        line_items=serialize_line_items(payload.line_items),
        notes=payload.notes,
    )
    db.add(invoice)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invoice already exists") from exc

    return _load_invoice_or_404(db, invoice.id)


@router.get("/public/{token}", response_model=PublicInvoiceResponse)
def get_public_invoice(token: UUID, db: Session = Depends(get_db)):
    invoice = _load_invoice_by_token_or_404(db, token)
    invoice_total = calculate_invoice_total(invoice.line_items)
    total_paid = Decimal("0.00")
    if invoice.payments:
        total_paid = sum(Decimal(str(payment.amount)) for payment in invoice.payments)
    amount_due = max(invoice_total - total_paid, Decimal("0.00"))

    client_secret: str | None = None
    if invoice.stripe_payment_intent_id:
        payment_intent = stripe.PaymentIntent.retrieve(invoice.stripe_payment_intent_id)
        if payment_intent["status"] != "cancelled":
            client_secret = payment_intent["client_secret"]

    if client_secret is None:
        payment_amount = amount_due if amount_due > Decimal("0.00") else invoice_total
        payment_intent = _create_payment_intent(invoice, payment_amount)
        invoice.stripe_payment_intent_id = payment_intent["id"]
        client_secret = payment_intent["client_secret"]

    if invoice.status == INVOICE_STATUS_SENT:
        invoice.status = INVOICE_STATUS_VIEWED

    db.commit()
    db.refresh(invoice)

    payload = InvoiceResponse.model_validate(invoice).model_dump()
    return PublicInvoiceResponse(**payload, stripe_client_secret=client_secret)


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
def send_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _load_invoice_or_404(db, invoice_id)
    if invoice.status != INVOICE_STATUS_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft invoices can be sent",
        )

    total = calculate_invoice_total(invoice.line_items)
    if total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice total must be greater than zero")

    payment_intent = _create_payment_intent(invoice, total)
    invoice.stripe_payment_intent_id = payment_intent["id"]
    invoice.status = INVOICE_STATUS_SENT

    payment_link = build_payment_link(settings.frontend_url, invoice.token)
    subject, body = _compose_initial_email(invoice)
    send_invoice_email(invoice.client.email, subject, body, payment_link)

    db.add(
        EmailLog(
            invoice_id=invoice.id,
            subject=subject,
            body=body,
            follow_up_day=INITIAL_FOLLOW_UP_DAY,
        )
    )
    db.commit()

    return _load_invoice_or_404(db, invoice.id)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return _load_invoice_or_404(db, invoice_id)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(invoice_id: int, payload: InvoiceUpdate, db: Session = Depends(get_db)):
    invoice = _load_invoice_or_404(db, invoice_id)
    updates = payload.model_dump(exclude_unset=True)

    if "status" in updates:
        try:
            updates["status"] = validate_invoice_status(updates["status"])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if "line_items" in updates and updates["line_items"] is not None:
        updates["line_items"] = serialize_line_items(updates["line_items"])

    if "due_date" in updates and updates["due_date"] is not None and updates["due_date"] < invoice.issue_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="due_date must be on or after issue_date",
        )

    for field_name, value in updates.items():
        setattr(invoice, field_name, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invoice already exists") from exc

    return _load_invoice_or_404(db, invoice.id)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _load_invoice_or_404(db, invoice_id)
    if invoice.status != INVOICE_STATUS_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft invoices can be deleted",
        )

    db.delete(invoice)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
