import json
import logging

import anthropic

from database import settings

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
        return json.loads(_extract_message_text(message))
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
