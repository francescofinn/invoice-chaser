from datetime import date, datetime

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from constants import (
    COLLECTION_CASE_STATUS_ACTION_READY,
    COLLECTION_CASE_STATUS_AWAITING_CLIENT,
    COLLECTION_CASE_STATUS_NEEDS_ANALYSIS,
    COLLECTION_CASE_STATUS_NEEDS_HUMAN_REVIEW,
    COLLECTION_CASE_STATUS_PAYMENT_PLAN,
    COLLECTION_CASE_STATUS_PROMISE_TO_PAY,
    COLLECTION_CASE_STATUS_RESOLVED,
    COLLECTION_COMMITMENT_STATUS_ACTIVE,
    COLLECTION_COMMITMENT_STATUS_SUPERSEDED,
    COLLECTION_RISK_LEVEL_HIGH,
    COLLECTION_RISK_LEVEL_MEDIUM,
    OUTSTANDING_INVOICE_STATUSES,
)
from database import get_db, settings
from models import CollectionActivity, CollectionCase, CollectionCommitment, Invoice
from schemas import (
    CashFlowForecastItem,
    ClientResponse,
    CollectionActivityResponse,
    CollectionCaseResponse,
    CollectionCommitmentResponse,
    InvoiceResponse,
    OperatorQueueItem,
    OperatorSendRequest,
    OperatorSimulateReplyRequest,
    OperatorSimulateReplyResponse,
)
from services import ai as ai_service
from services.collections import build_invoice_forecast_entries, calculate_remaining_amount
from services.email import send_invoice_email
from utils import build_payment_link

router = APIRouter()

RISK_PRIORITY = {
    COLLECTION_RISK_LEVEL_HIGH: 0,
    COLLECTION_RISK_LEVEL_MEDIUM: 1,
}


def _operator_invoice_options():
    return (
        joinedload(Invoice.client),
        selectinload(Invoice.payments),
        joinedload(Invoice.collection_case),
        selectinload(Invoice.collection_commitments),
        selectinload(Invoice.collection_activity),
    )


def _load_operator_invoice(db: Session, invoice_id: int) -> Invoice | None:
    statement = (
        select(Invoice)
        .options(*_operator_invoice_options())
        .where(Invoice.id == invoice_id, Invoice.status.in_(OUTSTANDING_INVOICE_STATUSES))
    )
    return db.scalars(statement).unique().one_or_none()


def _load_operator_invoice_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = _load_operator_invoice(db, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _ensure_collection_case(db: Session, invoice: Invoice) -> CollectionCase:
    if invoice.collection_case is not None:
        return invoice.collection_case

    collection_case = CollectionCase(invoice_id=invoice.id, status=COLLECTION_CASE_STATUS_NEEDS_ANALYSIS)
    db.add(collection_case)
    db.flush()
    invoice.collection_case = collection_case
    return collection_case


def _serialize_forecast_entries(entries: list[dict]) -> list[CashFlowForecastItem]:
    return [
        CashFlowForecastItem(
            date=entry["date"],
            expected_amount=float(entry["expected_amount"]),
            invoice_ids=entry["invoice_ids"],
        )
        for entry in entries
    ]


def _build_operator_queue_item(invoice: Invoice) -> OperatorQueueItem:
    collection_case = invoice.collection_case
    commitments = sorted(
        invoice.collection_commitments,
        key=lambda item: (item.due_date, item.created_at, item.id),
    )
    recent_activity = sorted(
        invoice.collection_activity,
        key=lambda item: (item.created_at, item.id),
        reverse=True,
    )[:8]
    return OperatorQueueItem(
        invoice=InvoiceResponse.model_validate(invoice),
        client=ClientResponse.model_validate(invoice.client),
        remaining_amount=calculate_remaining_amount(invoice),
        case=CollectionCaseResponse.model_validate(collection_case),
        commitments=[CollectionCommitmentResponse.model_validate(commitment) for commitment in commitments],
        recent_activity=[CollectionActivityResponse.model_validate(activity) for activity in recent_activity],
    )


def _build_invoice_context(invoice: Invoice) -> dict:
    remaining_amount = calculate_remaining_amount(invoice)
    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "issue_date": invoice.issue_date.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "days_overdue": max((date.today() - invoice.due_date).days, 0),
        "remaining_amount": str(remaining_amount),
    }


def _build_client_context(invoice: Invoice) -> dict:
    return {
        "name": invoice.client.name,
        "email": invoice.client.email,
        "company": invoice.client.company,
    }


def _build_payment_context(invoice: Invoice, collection_case: CollectionCase) -> dict:
    return {
        "remaining_amount": str(calculate_remaining_amount(invoice)),
        "payment_link": build_payment_link(settings.frontend_url, invoice.token),
        "last_contacted_at": collection_case.last_contacted_at.isoformat()
        if collection_case.last_contacted_at
        else None,
    }


def _build_next_action_from_reply(classification: str, commitments: list[dict]) -> tuple[str, str, str]:
    if classification == "promise_to_pay" and commitments:
        promised_date = commitments[0]["due_date"].isoformat()
        return (
            "monitor_promised_payment",
            "Check in after the promised payment date",
            f"The client committed to pay on {promised_date}, so the next step is to verify payment the following day.",
        )

    if classification == "payment_plan_request" and commitments:
        first_installment = commitments[0]["due_date"].isoformat()
        return (
            "monitor_installment_plan",
            "Track the next installment date",
            f"The client requested a split payment plan. Monitor the installment due on {first_installment} and follow up if it slips.",
        )

    if classification == "paid_elsewhere":
        return (
            "confirm_payment_reconciliation",
            "Verify payment reconciliation",
            "The client says payment was already sent, so the next step is to confirm the payment landed and reconcile the invoice.",
        )

    return (
        "human_review",
        "Review the client reply manually",
        "The reply needs a person to confirm intent before the next outreach is sent.",
    )


def _queue_sort_key(invoice: Invoice):
    collection_case = invoice.collection_case
    remaining_amount = calculate_remaining_amount(invoice)
    return (
        0 if invoice.status == "overdue" else 1,
        RISK_PRIORITY.get(collection_case.risk_level, 2),
        -remaining_amount,
        collection_case.last_contacted_at or datetime.min,
    )


@router.get("/cases", response_model=list[OperatorQueueItem])
def list_operator_cases(db: Session = Depends(get_db)):
    invoices = db.scalars(
        select(Invoice)
        .options(*_operator_invoice_options())
        .where(Invoice.status.in_(OUTSTANDING_INVOICE_STATUSES))
    ).unique().all()

    created_any_case = False
    for invoice in invoices:
        if invoice.collection_case is None:
            _ensure_collection_case(db, invoice)
            created_any_case = True

    if created_any_case:
        db.commit()

    return [_build_operator_queue_item(invoice) for invoice in sorted(invoices, key=_queue_sort_key)]


@router.post("/cases/{invoice_id}/analyze", response_model=OperatorQueueItem)
def analyze_operator_case(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _load_operator_invoice_or_404(db, invoice_id)
    collection_case = _ensure_collection_case(db, invoice)

    analysis = ai_service.generate_operator_analysis(
        _build_invoice_context(invoice),
        _build_client_context(invoice),
        _build_payment_context(invoice, collection_case),
    )

    collection_case.status = COLLECTION_CASE_STATUS_ACTION_READY
    collection_case.risk_level = analysis["risk_level"]
    collection_case.risk_summary = analysis["risk_summary"]
    collection_case.next_action_key = analysis["next_action_key"]
    collection_case.next_action_label = analysis["next_action_label"]
    collection_case.next_action_reason = analysis["next_action_reason"]
    collection_case.draft_subject = analysis["draft_subject"]
    collection_case.draft_body = analysis["draft_body"]
    collection_case.last_analyzed_at = datetime.utcnow()

    db.add(
        CollectionActivity(
            invoice_id=invoice.id,
            activity_type="analysis_generated",
            title=f"Analysis ready: {collection_case.next_action_label}",
            body=collection_case.risk_summary,
            payload_json=analysis,
        )
    )
    db.commit()

    refreshed_invoice = _load_operator_invoice_or_404(db, invoice_id)
    return _build_operator_queue_item(refreshed_invoice)


@router.post("/cases/{invoice_id}/send", response_model=OperatorQueueItem)
def send_operator_case(
    invoice_id: int,
    payload: OperatorSendRequest | None = Body(default=None),
    db: Session = Depends(get_db),
):
    invoice = _load_operator_invoice_or_404(db, invoice_id)
    collection_case = _ensure_collection_case(db, invoice)
    payload = payload or OperatorSendRequest()

    if payload.draft_subject is not None:
        collection_case.draft_subject = payload.draft_subject
    if payload.draft_body is not None:
        collection_case.draft_body = payload.draft_body

    if not collection_case.draft_subject or not collection_case.draft_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft subject and body are required before sending",
        )

    remaining_amount = calculate_remaining_amount(invoice)
    if remaining_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice has no remaining balance to collect",
        )

    message_id = send_invoice_email(
        invoice.client.email,
        collection_case.draft_subject,
        collection_case.draft_body,
        build_payment_link(settings.frontend_url, invoice.token),
        invoice_number=invoice.invoice_number,
        amount=str(remaining_amount),
        due_date=invoice.due_date.isoformat(),
        is_overdue=invoice.status == "overdue",
    )

    collection_case.status = COLLECTION_CASE_STATUS_AWAITING_CLIENT
    collection_case.last_contacted_at = datetime.utcnow()

    db.add(
        CollectionActivity(
            invoice_id=invoice.id,
            activity_type="operator_email_sent",
            title="Operator draft sent",
            body=collection_case.draft_body,
            payload_json={
                "message_id": message_id,
                "subject": collection_case.draft_subject,
                "remaining_amount": str(remaining_amount),
            },
        )
    )
    db.commit()

    refreshed_invoice = _load_operator_invoice_or_404(db, invoice_id)
    return _build_operator_queue_item(refreshed_invoice)


@router.post("/cases/{invoice_id}/simulate-reply", response_model=OperatorSimulateReplyResponse)
def simulate_operator_reply(
    invoice_id: int,
    payload: OperatorSimulateReplyRequest,
    db: Session = Depends(get_db),
):
    invoice = _load_operator_invoice_or_404(db, invoice_id)
    collection_case = _ensure_collection_case(db, invoice)
    active_commitments = [
        commitment
        for commitment in invoice.collection_commitments
        if commitment.status == COLLECTION_COMMITMENT_STATUS_ACTIVE
    ]
    forecast_before = _serialize_forecast_entries(
        build_invoice_forecast_entries(invoice, active_commitments=active_commitments)
    )

    db.add(
        CollectionActivity(
            invoice_id=invoice.id,
            activity_type="simulated_reply_received",
            title="Simulated client reply received",
            body=payload.reply_text,
            payload_json={"reply_text": payload.reply_text},
        )
    )

    reply_result = ai_service.classify_operator_reply(_build_invoice_context(invoice), payload.reply_text)

    for commitment in active_commitments:
        commitment.status = COLLECTION_COMMITMENT_STATUS_SUPERSEDED

    new_commitments = []
    for commitment_payload in reply_result["commitments"]:
        commitment = CollectionCommitment(
            invoice_id=invoice.id,
            commitment_type=commitment_payload["commitment_type"],
            due_date=commitment_payload["due_date"],
            amount=commitment_payload["amount"],
            status=COLLECTION_COMMITMENT_STATUS_ACTIVE,
            source="simulated_reply",
        )
        new_commitments.append(commitment)
        db.add(commitment)

    next_action_key, next_action_label, next_action_reason = _build_next_action_from_reply(
        reply_result["classification"],
        reply_result["commitments"],
    )
    collection_case.status = reply_result["next_case_status"]
    collection_case.last_client_reply = payload.reply_text
    collection_case.last_reply_classification = reply_result["classification"]
    collection_case.queued_follow_up_date = reply_result["queued_follow_up_date"]
    collection_case.next_action_key = next_action_key
    collection_case.next_action_label = next_action_label
    collection_case.next_action_reason = next_action_reason

    db.add(
        CollectionActivity(
            invoice_id=invoice.id,
            activity_type="reply_classified",
            title=f"Reply classified as {reply_result['classification']}",
            body=reply_result["rationale"],
            payload_json={
                "classification": reply_result["classification"],
                "queued_follow_up_date": reply_result["queued_follow_up_date"].isoformat()
                if reply_result["queued_follow_up_date"]
                else None,
                "next_case_status": reply_result["next_case_status"],
            },
        )
    )
    db.commit()

    refreshed_invoice = _load_operator_invoice_or_404(db, invoice_id)
    forecast_after = _serialize_forecast_entries(build_invoice_forecast_entries(refreshed_invoice))
    operator_queue_item = _build_operator_queue_item(refreshed_invoice)
    return OperatorSimulateReplyResponse(
        **operator_queue_item.model_dump(),
        forecast_before=forecast_before,
        forecast_after=forecast_after,
    )
