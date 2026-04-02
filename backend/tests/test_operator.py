from datetime import date, datetime, timedelta
from decimal import Decimal

from conftest import (
    create_client,
    create_collection_case,
    create_collection_commitment,
    create_invoice,
)
from models import CollectionActivity, CollectionCase, CollectionCommitment, EmailLog


def _next_weekday(target_weekday: int, *, from_date: date | None = None) -> date:
    reference = from_date or date.today()
    days_ahead = (target_weekday - reference.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return reference + timedelta(days=days_ahead)


def test_operator_analyze_persists_case_details(client, db_session, monkeypatch):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-OP-001",
        status="overdue",
        due_date=date.today() - timedelta(days=9),
        line_items=[{"description": "Retainer", "quantity": "1", "unit_price": "2400.00"}],
    )

    analysis_payload = {
        "risk_level": "high",
        "risk_summary": "The invoice is materially overdue and there has been no confirmed payment activity.",
        "next_action_key": "send_firm_follow_up",
        "next_action_label": "Send a firm follow-up",
        "next_action_reason": "A direct outreach is the fastest way to clarify intent and secure a payment date.",
        "draft_subject": "Checking in on invoice INV-OP-001",
        "draft_body": "Hi Alice, can you confirm when we should expect payment for INV-OP-001?",
    }

    monkeypatch.setattr("services.ai.generate_operator_analysis", lambda *args, **kwargs: analysis_payload)

    response = client.post(f"/operator/cases/{invoice.id}/analyze")

    assert response.status_code == 200
    body = response.json()
    assert body["case"]["status"] == "action_ready"
    assert body["case"]["risk_level"] == "high"
    assert body["case"]["draft_subject"] == analysis_payload["draft_subject"]

    collection_case = db_session.query(CollectionCase).filter_by(invoice_id=invoice.id).one()
    assert collection_case.status == "action_ready"
    assert collection_case.risk_summary == analysis_payload["risk_summary"]
    assert collection_case.last_analyzed_at is not None

    activity = (
        db_session.query(CollectionActivity)
        .filter_by(invoice_id=invoice.id, activity_type="analysis_generated")
        .one()
    )
    assert "Send a firm follow-up" in activity.title


def test_operator_send_uses_current_draft_and_tracks_activity(client, db_session, monkeypatch):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-OP-002",
        status="overdue",
        due_date=date.today() - timedelta(days=15),
        line_items=[{"description": "Audit", "quantity": "1", "unit_price": "1800.00"}],
    )
    create_collection_case(
        db_session,
        invoice.id,
        status="action_ready",
        draft_subject="Draft subject",
        draft_body="Draft body",
    )

    sent_message = {}

    def fake_send_invoice_email(to_email, subject, body, payment_link, **kwargs):
        sent_message.update(
            {
                "to_email": to_email,
                "subject": subject,
                "body": body,
                "payment_link": payment_link,
                "metadata": kwargs,
            }
        )
        return "re_operator_123"

    monkeypatch.setattr("routers.operator.send_invoice_email", fake_send_invoice_email)

    response = client.post(
        f"/operator/cases/{invoice.id}/send",
        json={"draft_subject": "Updated subject", "draft_body": "Updated body"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["case"]["status"] == "awaiting_client"
    assert body["case"]["last_contacted_at"] is not None

    db_case = db_session.query(CollectionCase).filter_by(invoice_id=invoice.id).one()
    assert db_case.draft_subject == "Updated subject"
    assert db_case.draft_body == "Updated body"
    assert db_case.last_contacted_at is not None

    activity = (
        db_session.query(CollectionActivity)
        .filter_by(invoice_id=invoice.id, activity_type="operator_email_sent")
        .one()
    )
    assert activity.title == "Operator draft sent"
    assert activity.payload_json["message_id"] == "re_operator_123"
    assert db_session.query(EmailLog).filter_by(invoice_id=invoice.id).count() == 0

    assert sent_message["to_email"] == db_client.email
    assert sent_message["subject"] == "Updated subject"
    assert sent_message["body"] == "Updated body"
    assert sent_message["metadata"]["invoice_number"] == invoice.invoice_number


def test_operator_send_uses_persisted_draft_when_body_is_omitted(client, db_session, monkeypatch):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-OP-002B",
        status="sent",
        due_date=date.today() + timedelta(days=5),
        line_items=[{"description": "Advisory", "quantity": "1", "unit_price": "950.00"}],
    )
    create_collection_case(
        db_session,
        invoice.id,
        status="action_ready",
        draft_subject="Stored subject",
        draft_body="Stored body",
    )

    captured = {}

    def fake_send_invoice_email(to_email, subject, body, payment_link, **kwargs):
        captured.update({"to_email": to_email, "subject": subject, "body": body, "payment_link": payment_link})
        return "re_operator_456"

    monkeypatch.setattr("routers.operator.send_invoice_email", fake_send_invoice_email)

    response = client.post(f"/operator/cases/{invoice.id}/send")

    assert response.status_code == 200
    assert captured["to_email"] == db_client.email
    assert captured["subject"] == "Stored subject"
    assert captured["body"] == "Stored body"


def test_operator_simulate_reply_falls_back_to_payment_plan_and_replaces_commitments(
    client,
    db_session,
    monkeypatch,
):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-OP-003",
        status="overdue",
        due_date=date.today() - timedelta(days=12),
        line_items=[{"description": "Implementation", "quantity": "1", "unit_price": "1000.00"}],
    )
    create_collection_case(
        db_session,
        invoice.id,
        status="awaiting_client",
        last_contacted_at=datetime.utcnow(),
    )
    existing_commitment = create_collection_commitment(
        db_session,
        invoice.id,
        due_date=date.today() + timedelta(days=1),
        amount="1000.00",
        source="prior_reply",
    )

    def raise_for_ai(*args, **kwargs):
        raise RuntimeError("Anthropic unavailable")

    monkeypatch.setattr("services.ai.client.messages.create", raise_for_ai)

    response = client.post(
        f"/operator/cases/{invoice.id}/simulate-reply",
        json={"reply_text": "Can I pay half now and the rest Friday?"},
    )

    assert response.status_code == 200
    body = response.json()
    expected_second_due_date = _next_weekday(4).isoformat()

    assert body["case"]["status"] == "payment_plan"
    assert body["case"]["last_reply_classification"] == "payment_plan_request"
    assert body["case"]["queued_follow_up_date"] == (
        _next_weekday(4) + timedelta(days=1)
    ).isoformat()
    assert len(body["commitments"]) == 3
    assert len(body["forecast_before"]) == 1
    assert len(body["forecast_after"]) == 2

    db_session.refresh(existing_commitment)
    assert existing_commitment.status == "superseded"

    active_commitments = (
        db_session.query(CollectionCommitment)
        .filter_by(invoice_id=invoice.id, status="active")
        .order_by(CollectionCommitment.due_date.asc(), CollectionCommitment.id.asc())
        .all()
    )
    assert [commitment.commitment_type for commitment in active_commitments] == [
        "payment_plan_installment",
        "payment_plan_installment",
    ]
    assert [str(commitment.amount) for commitment in active_commitments] == ["500.00", "500.00"]
    assert active_commitments[0].due_date.isoformat() == date.today().isoformat()
    assert active_commitments[1].due_date.isoformat() == expected_second_due_date


def test_operator_simulate_reply_creates_promise_to_pay_commitment_and_forecast(
    client,
    db_session,
    monkeypatch,
):
    db_client = create_client(db_session)
    promise_date = date.today() + timedelta(days=6)
    invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-OP-004",
        status="sent",
        due_date=date.today() + timedelta(days=20),
        line_items=[{"description": "Consulting", "quantity": "1", "unit_price": "750.00"}],
    )
    create_collection_case(
        db_session,
        invoice.id,
        status="awaiting_client",
        last_contacted_at=datetime.utcnow(),
    )

    monkeypatch.setattr(
        "services.ai.client.messages.create",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Anthropic unavailable")),
    )

    response = client.post(
        f"/operator/cases/{invoice.id}/simulate-reply",
        json={"reply_text": f"I can pay the full amount on {promise_date.isoformat()}."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["case"]["status"] == "promise_to_pay"
    assert body["case"]["last_reply_classification"] == "promise_to_pay"
    assert body["case"]["queued_follow_up_date"] == (promise_date + timedelta(days=1)).isoformat()
    assert len(body["forecast_before"]) == 1
    assert body["forecast_before"][0]["date"] == invoice.due_date.isoformat()
    assert len(body["forecast_after"]) == 1
    assert body["forecast_after"][0]["date"] == promise_date.isoformat()
    assert body["forecast_after"][0]["expected_amount"] == 750.0

    commitment = (
        db_session.query(CollectionCommitment)
        .filter_by(invoice_id=invoice.id, status="active")
        .one()
    )
    assert commitment.commitment_type == "promise_to_pay"
    assert commitment.due_date == promise_date
    assert Decimal(str(commitment.amount)) == Decimal("750.00")


def test_operator_queue_orders_by_overdue_risk_balance_and_contact(client, db_session):
    db_client = create_client(db_session)

    overdue_invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-OP-101",
        status="overdue",
        due_date=date.today() - timedelta(days=20),
        line_items=[{"description": "A", "quantity": "1", "unit_price": "300.00"}],
    )
    high_balance_invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-OP-102",
        status="sent",
        due_date=date.today() + timedelta(days=10),
        line_items=[{"description": "B", "quantity": "1", "unit_price": "900.00"}],
    )
    medium_older_invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-OP-103",
        status="viewed",
        due_date=date.today() + timedelta(days=12),
        line_items=[{"description": "C", "quantity": "1", "unit_price": "600.00"}],
    )
    medium_newer_invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-OP-104",
        status="viewed",
        due_date=date.today() + timedelta(days=14),
        line_items=[{"description": "D", "quantity": "1", "unit_price": "600.00"}],
    )
    low_invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-OP-105",
        status="sent",
        due_date=date.today() + timedelta(days=18),
        line_items=[{"description": "E", "quantity": "1", "unit_price": "1200.00"}],
    )

    create_collection_case(
        db_session,
        overdue_invoice.id,
        status="action_ready",
        risk_level="low",
        last_contacted_at=datetime.utcnow() - timedelta(days=7),
    )
    create_collection_case(
        db_session,
        high_balance_invoice.id,
        status="action_ready",
        risk_level="high",
        last_contacted_at=datetime.utcnow() - timedelta(days=1),
    )
    create_collection_case(
        db_session,
        medium_older_invoice.id,
        status="action_ready",
        risk_level="medium",
        last_contacted_at=datetime.utcnow() - timedelta(days=6),
    )
    create_collection_case(
        db_session,
        medium_newer_invoice.id,
        status="action_ready",
        risk_level="medium",
        last_contacted_at=datetime.utcnow() - timedelta(days=2),
    )
    create_collection_case(
        db_session,
        low_invoice.id,
        status="action_ready",
        risk_level="low",
        last_contacted_at=datetime.utcnow() - timedelta(days=10),
    )

    response = client.get("/operator/cases")

    assert response.status_code == 200
    ordered_invoice_ids = [item["invoice"]["id"] for item in response.json()]
    assert ordered_invoice_ids == [
        overdue_invoice.id,
        high_balance_invoice.id,
        medium_older_invoice.id,
        medium_newer_invoice.id,
        low_invoice.id,
    ]
