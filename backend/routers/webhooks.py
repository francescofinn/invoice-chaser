from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from constants import INVOICE_STATUS_PAID, INVOICE_STATUS_PARTIALLY_PAID
from database import get_db, settings
from models import Invoice, Payment
from utils import calculate_invoice_total, calculate_payment_total

stripe.api_key = settings.stripe_secret_key

router = APIRouter()


@router.post("/stripe")
async def handle_stripe_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(raw_body, signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature") from exc

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        invoice_id = int(payment_intent["metadata"]["invoice_id"])
        amount_paid = (Decimal(payment_intent["amount_received"]) / Decimal("100")).quantize(Decimal("0.01"))

        invoice = db.scalars(
            select(Invoice).options(joinedload(Invoice.payments)).where(Invoice.id == invoice_id)
        ).unique().one_or_none()
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

        existing_payment = db.scalars(
            select(Payment).where(Payment.stripe_payment_intent_id == payment_intent["id"])
        ).one_or_none()
        if not existing_payment:
            db.add(
                Payment(
                    invoice_id=invoice_id,
                    amount=amount_paid,
                    stripe_payment_intent_id=payment_intent["id"],
                )
            )

        total_paid = calculate_payment_total(invoice.payments)
        if not existing_payment:
            total_paid += amount_paid
        invoice_total = calculate_invoice_total(invoice.line_items)
        invoice.status = (
            INVOICE_STATUS_PAID if total_paid >= invoice_total else INVOICE_STATUS_PARTIALLY_PAID
        )
        db.commit()

    return {"status": "ok"}
