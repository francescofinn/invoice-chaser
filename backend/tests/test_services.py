import json
from types import SimpleNamespace

import pytest

from services.ai import generate_follow_up_email
from services.email import send_invoice_email


def test_send_invoice_email_builds_expected_resend_payload(monkeypatch):
    sent_payload = {}

    def fake_send(payload):
        sent_payload.update(payload)
        return {"id": "re_123"}

    monkeypatch.setattr("services.email.resend.Emails.send", fake_send)

    message_id = send_invoice_email(
        "alice@example.com",
        "Invoice INV-001",
        "Please review your invoice.",
        "http://localhost:5173/pay/token-123",
    )

    assert message_id == "re_123"
    assert sent_payload["to"] == ["alice@example.com"]
    assert "Pay Now" in sent_payload["html"]


def test_generate_follow_up_email_returns_ai_json_on_success(monkeypatch):
    response_body = {"subject": "Invoice INV-001 is overdue", "body": "Please pay promptly."}

    def fake_create(**kwargs):
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(response_body))])

    monkeypatch.setattr("services.ai.client.messages.create", fake_create)

    result = generate_follow_up_email(
        "Alice",
        "INV-001",
        "250.00",
        "2026-04-01",
        3,
        "http://localhost:5173/pay/token-123",
        3,
    )

    assert result == response_body


@pytest.mark.parametrize(
    ("follow_up_day", "expected_subject"),
    [
        (3, "Friendly reminder: Invoice INV-001 due"),
        (7, "Invoice INV-001 is overdue"),
        (14, "Urgent: Invoice INV-001 requires immediate attention"),
    ],
)
def test_generate_follow_up_email_falls_back_when_ai_fails(
    monkeypatch,
    follow_up_day,
    expected_subject,
):
    def fake_create(**kwargs):
        raise RuntimeError("Anthropic unavailable")

    monkeypatch.setattr("services.ai.client.messages.create", fake_create)

    result = generate_follow_up_email(
        "Alice",
        "INV-001",
        "250.00",
        "2026-04-01",
        follow_up_day,
        "http://localhost:5173/pay/token-123",
        follow_up_day,
    )

    assert result["subject"] == expected_subject
    assert "INV-001" in result["body"]
