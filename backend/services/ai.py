import json
import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

import anthropic

from constants import (
    COLLECTION_CASE_STATUS_NEEDS_HUMAN_REVIEW,
    COLLECTION_CASE_STATUS_PAYMENT_PLAN,
    COLLECTION_CASE_STATUS_PROMISE_TO_PAY,
    COLLECTION_CASE_STATUS_RESOLVED,
    COLLECTION_COMMITMENT_TYPE_PAYMENT_PLAN_INSTALLMENT,
    COLLECTION_COMMITMENT_TYPE_PROMISE_TO_PAY,
    COLLECTION_REPLY_CLASSIFICATION_DISPUTE,
    COLLECTION_REPLY_CLASSIFICATION_PAID_ELSEWHERE,
    COLLECTION_REPLY_CLASSIFICATION_PAYMENT_PLAN_REQUEST,
    COLLECTION_REPLY_CLASSIFICATION_PROMISE_TO_PAY,
    COLLECTION_REPLY_CLASSIFICATION_QUESTION,
    COLLECTION_REPLY_CLASSIFICATION_UNKNOWN,
    COLLECTION_RISK_LEVEL_HIGH,
    COLLECTION_RISK_LEVEL_LOW,
    COLLECTION_RISK_LEVEL_MEDIUM,
)
from database import settings
from utils import normalize_money

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
logger = logging.getLogger(__name__)

TONE_MAP = {
    3: "friendly and gentle - assume the client may have simply forgotten",
    7: "professional and direct - politely but clearly state the invoice is overdue",
    14: "firm and urgent - make clear that further action may be taken if not resolved promptly",
}

FALLBACK = {
    3: {
        "subject": "Friendly reminder: Invoice {num} due",
        "body": "Hi {name},\n\nJust a quick reminder that invoice {num} for ${amount} was due on {due_date}. Please pay at: {link}",
    },
    7: {
        "subject": "Invoice {num} is overdue",
        "body": "Hi {name},\n\nInvoice {num} for ${amount} (due {due_date}) remains unpaid. Please settle at: {link}",
    },
    14: {
        "subject": "Urgent: Invoice {num} requires immediate attention",
        "body": "Hi {name},\n\nInvoice {num} for ${amount} is now 14 days overdue. Immediate payment is required: {link}",
    },
}


def _extract_message_text(message) -> str:
    first_block = message.content[0]
    if hasattr(first_block, "text"):
        return first_block.text
    return first_block["text"]


def generate_follow_up_email(
    client_name,
    invoice_number,
    amount_due,
    due_date,
    days_overdue,
    payment_link,
    follow_up_day,
) -> dict:
    tone = TONE_MAP.get(follow_up_day, TONE_MAP[3])
    prompt = (
        "Write a payment follow-up email for a small business owner.\n"
        f"Client: {client_name} | Invoice: {invoice_number} | Amount: ${amount_due} | Due: {due_date} | Days overdue: {days_overdue}\n"
        f"Payment link: {payment_link}\n"
        f"Tone: {tone}\n"
        'Keep it 3-5 sentences. Return ONLY valid JSON with keys "subject" and "body". No other text.'
    )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = _extract_message_text(message).strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0].strip()
        return json.loads(text)
    except Exception as exc:
        logger.error("AI generation failed: %s", exc)
        template = FALLBACK.get(follow_up_day, FALLBACK[3])
        return {
            "subject": template["subject"].format(num=invoice_number),
            "body": template["body"].format(
                name=client_name,
                num=invoice_number,
                amount=amount_due,
                due_date=due_date,
                link=payment_link,
            ),
        }


def _call_model_for_json(prompt: str, *, max_tokens: int = 1024) -> dict:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(_extract_message_text(message))


def _coerce_date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()

    value = str(value).strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _parse_month_date(value: str, reference_date: date) -> date | None:
    normalized = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", value, flags=re.IGNORECASE)
    for pattern in ("%B %d %Y", "%b %d %Y", "%B %d", "%b %d"):
        try:
            parsed = datetime.strptime(normalized, pattern)
        except ValueError:
            continue
        if "%Y" in pattern:
            return parsed.date()

        candidate = parsed.replace(year=reference_date.year).date()
        if candidate < reference_date:
            candidate = candidate.replace(year=reference_date.year + 1)
        return candidate
    return None


def _parse_future_date(reply_text: str, reference_date: date) -> date | None:
    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", reply_text)
    if iso_match:
        parsed = _coerce_date(iso_match.group(1))
        if parsed and parsed > reference_date:
            return parsed

    us_match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", reply_text)
    if us_match:
        parsed = _coerce_date(us_match.group(1))
        if parsed and parsed > reference_date:
            return parsed

    month_match = re.search(
        r"\b((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
        r"dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?)\b",
        reply_text,
        flags=re.IGNORECASE,
    )
    if month_match:
        parsed = _parse_month_date(month_match.group(1).replace(",", ""), reference_date)
        if parsed and parsed > reference_date:
            return parsed

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    lowered = reply_text.lower()
    for weekday_name, weekday_index in weekdays.items():
        if re.search(rf"\b(?:next\s+)?{weekday_name}\b", lowered):
            days_ahead = (weekday_index - reference_date.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return reference_date + timedelta(days=days_ahead)

    return None


def _build_fallback_operator_analysis(invoice_context, client_context, payment_context) -> dict:
    days_overdue = invoice_context["days_overdue"]
    remaining_amount = normalize_money(payment_context["remaining_amount"])
    due_date = invoice_context["due_date"]
    payment_link = payment_context["payment_link"]
    client_name = client_context["name"]

    if days_overdue >= 14 or remaining_amount >= Decimal("5000.00"):
        risk_level = COLLECTION_RISK_LEVEL_HIGH
        next_action_key = "send_firm_follow_up"
        next_action_label = "Send a firm follow-up"
        next_action_reason = "The balance is aging and needs a direct ask for a concrete payment date."
    elif days_overdue >= 7 or remaining_amount >= Decimal("2000.00"):
        risk_level = COLLECTION_RISK_LEVEL_MEDIUM
        next_action_key = "send_direct_reminder"
        next_action_label = "Send a direct reminder"
        next_action_reason = "The account needs a prompt nudge before it slips further."
    else:
        risk_level = COLLECTION_RISK_LEVEL_LOW
        next_action_key = "send_friendly_check_in"
        next_action_label = "Send a friendly check-in"
        next_action_reason = "A light touch is appropriate while the invoice is still relatively fresh."

    if days_overdue > 0:
        risk_summary = (
            f"{client_name} is {days_overdue} days past due on invoice {invoice_context['invoice_number']} "
            f"with ${remaining_amount} still outstanding."
        )
    else:
        risk_summary = (
            f"Invoice {invoice_context['invoice_number']} is due on {due_date} with ${remaining_amount} still open."
        )

    draft_subject = f"Checking in on invoice {invoice_context['invoice_number']}"
    draft_body = (
        f"Hi {client_name},\n\n"
        f"I’m following up on invoice {invoice_context['invoice_number']} for ${remaining_amount}, "
        f"which was due on {due_date}. Please let me know if payment is in progress or if you need a short plan.\n\n"
        f"You can pay here: {payment_link}"
    )

    return {
        "risk_level": risk_level,
        "risk_summary": risk_summary,
        "next_action_key": next_action_key,
        "next_action_label": next_action_label,
        "next_action_reason": next_action_reason,
        "draft_subject": draft_subject,
        "draft_body": draft_body,
    }


def generate_operator_analysis(invoice_context, client_context, payment_context) -> dict:
    prompt = (
        "You are an accounts receivable collections operator.\n"
        "Review the invoice, client, and payment context and propose the next best action.\n"
        "Return ONLY valid JSON with keys "
        '"risk_level", "risk_summary", "next_action_key", "next_action_label", '
        '"next_action_reason", "draft_subject", and "draft_body".\n'
        f"Invoice context: {json.dumps(invoice_context)}\n"
        f"Client context: {json.dumps(client_context)}\n"
        f"Payment context: {json.dumps(payment_context)}"
    )

    fallback = _build_fallback_operator_analysis(invoice_context, client_context, payment_context)
    try:
        payload = _call_model_for_json(prompt)
        return {
            "risk_level": str(payload.get("risk_level", fallback["risk_level"])).lower(),
            "risk_summary": payload.get("risk_summary") or fallback["risk_summary"],
            "next_action_key": payload.get("next_action_key") or fallback["next_action_key"],
            "next_action_label": payload.get("next_action_label") or fallback["next_action_label"],
            "next_action_reason": payload.get("next_action_reason") or fallback["next_action_reason"],
            "draft_subject": payload.get("draft_subject") or fallback["draft_subject"],
            "draft_body": payload.get("draft_body") or fallback["draft_body"],
        }
    except Exception as exc:
        logger.error("Operator analysis failed: %s", exc)
        return fallback


def _build_payment_plan_commitments(remaining_amount: Decimal, promised_date: date) -> list[dict]:
    first_amount = (remaining_amount / Decimal("2")).quantize(Decimal("0.01"))
    second_amount = normalize_money(remaining_amount - first_amount)
    return [
        {
            "commitment_type": COLLECTION_COMMITMENT_TYPE_PAYMENT_PLAN_INSTALLMENT,
            "due_date": date.today(),
            "amount": first_amount,
        },
        {
            "commitment_type": COLLECTION_COMMITMENT_TYPE_PAYMENT_PLAN_INSTALLMENT,
            "due_date": promised_date,
            "amount": second_amount,
        },
    ]


def _build_promise_commitment(remaining_amount: Decimal, promised_date: date) -> list[dict]:
    return [
        {
            "commitment_type": COLLECTION_COMMITMENT_TYPE_PROMISE_TO_PAY,
            "due_date": promised_date,
            "amount": normalize_money(remaining_amount),
        }
    ]


def _build_fallback_reply_classification(invoice_context, reply_text: str) -> dict:
    lowered = reply_text.lower()
    today = date.today()
    remaining_amount = normalize_money(invoice_context["remaining_amount"])
    promised_date = _parse_future_date(reply_text, today)

    if "already paid" in lowered:
        return {
            "classification": COLLECTION_REPLY_CLASSIFICATION_PAID_ELSEWHERE,
            "rationale": "The client says payment has already been made elsewhere.",
            "commitments": [],
            "queued_follow_up_date": None,
            "next_case_status": COLLECTION_CASE_STATUS_RESOLVED,
        }

    if "wrong invoice" in lowered or "dispute" in lowered:
        return {
            "classification": COLLECTION_REPLY_CLASSIFICATION_DISPUTE,
            "rationale": "The client is disputing the invoice and needs manual review.",
            "commitments": [],
            "queued_follow_up_date": None,
            "next_case_status": COLLECTION_CASE_STATUS_NEEDS_HUMAN_REVIEW,
        }

    split_language = "half" in lowered or "split" in lowered or "payment plan" in lowered
    if split_language and promised_date:
        return {
            "classification": COLLECTION_REPLY_CLASSIFICATION_PAYMENT_PLAN_REQUEST,
            "rationale": "The client requested a split payment schedule with a future date.",
            "commitments": _build_payment_plan_commitments(remaining_amount, promised_date),
            "queued_follow_up_date": promised_date + timedelta(days=1),
            "next_case_status": COLLECTION_CASE_STATUS_PAYMENT_PLAN,
        }

    if promised_date:
        return {
            "classification": COLLECTION_REPLY_CLASSIFICATION_PROMISE_TO_PAY,
            "rationale": "The client committed to a specific future payment date.",
            "commitments": _build_promise_commitment(remaining_amount, promised_date),
            "queued_follow_up_date": promised_date + timedelta(days=1),
            "next_case_status": COLLECTION_CASE_STATUS_PROMISE_TO_PAY,
        }

    if "issue" in lowered or "question" in lowered or "?" in lowered:
        return {
            "classification": COLLECTION_REPLY_CLASSIFICATION_QUESTION,
            "rationale": "The client is raising a question that needs a human response.",
            "commitments": [],
            "queued_follow_up_date": None,
            "next_case_status": COLLECTION_CASE_STATUS_NEEDS_HUMAN_REVIEW,
        }

    return {
        "classification": COLLECTION_REPLY_CLASSIFICATION_UNKNOWN,
        "rationale": "The reply did not include a reliable payment commitment.",
        "commitments": [],
        "queued_follow_up_date": None,
        "next_case_status": COLLECTION_CASE_STATUS_NEEDS_HUMAN_REVIEW,
    }


def _normalize_commitment_payload(commitment: dict) -> dict:
    return {
        "commitment_type": str(commitment["commitment_type"]).lower(),
        "due_date": _coerce_date(commitment["due_date"]),
        "amount": normalize_money(commitment["amount"]),
    }


def classify_operator_reply(invoice_context, reply_text: str) -> dict:
    prompt = (
        "You are classifying a client collections reply.\n"
        "Return ONLY valid JSON with keys "
        '"classification", "rationale", "commitments", "queued_follow_up_date", and "next_case_status".\n'
        "The commitments array must contain objects with commitment_type, due_date, and amount.\n"
        f"Invoice context: {json.dumps(invoice_context)}\n"
        f"Reply: {reply_text}"
    )

    fallback = _build_fallback_reply_classification(invoice_context, reply_text)
    try:
        payload = _call_model_for_json(prompt)
        commitments = [
            _normalize_commitment_payload(commitment)
            for commitment in payload.get("commitments", [])
            if commitment.get("due_date") and commitment.get("amount") is not None
        ]
        return {
            "classification": str(payload.get("classification", fallback["classification"])).lower(),
            "rationale": payload.get("rationale") or fallback["rationale"],
            "commitments": commitments or fallback["commitments"],
            "queued_follow_up_date": _coerce_date(payload.get("queued_follow_up_date"))
            or fallback["queued_follow_up_date"],
            "next_case_status": payload.get("next_case_status") or fallback["next_case_status"],
        }
    except Exception as exc:
        logger.error("Operator reply classification failed: %s", exc)
        return fallback
