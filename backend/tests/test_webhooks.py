from datetime import date

from conftest import create_client, create_invoice


def test_valid_webhook_creates_payment_and_updates_invoice_status(client, db_session, monkeypatch):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        status="sent",
        issue_date=date(2026, 4, 1),
        due_date=date(2026, 4, 30),
        line_items=[{"description": "Strategy", "quantity": "2", "unit_price": "100.00"}],
    )

    monkeypatch.setattr(
        "routers.webhooks.stripe.Webhook.construct_event",
        lambda payload, sig_header, secret: {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_paid_123",
                    "amount_received": 20000,
                    "metadata": {"invoice_id": str(invoice.id)},
                }
            },
        },
    )

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "sig_123"},
    )

    assert response.status_code == 200
    refreshed = db_session.get(type(invoice), invoice.id)
    assert refreshed.status == "paid"
    assert len(refreshed.payments) == 1


def test_duplicate_webhook_does_not_duplicate_payment(client, db_session, monkeypatch):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        status="sent",
        line_items=[{"description": "Strategy", "quantity": "2", "unit_price": "100.00"}],
    )

    event = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_paid_123",
                "amount_received": 10000,
                "metadata": {"invoice_id": str(invoice.id)},
            }
        },
    }
    monkeypatch.setattr("routers.webhooks.stripe.Webhook.construct_event", lambda *args, **kwargs: event)

    first_response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "sig_123"},
    )
    second_response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "sig_123"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    refreshed = db_session.get(type(invoice), invoice.id)
    assert len(refreshed.payments) == 1


def test_invalid_signature_returns_400(client, monkeypatch):
    def fake_construct_event(*args, **kwargs):
        raise ValueError("Invalid signature")

    monkeypatch.setattr("routers.webhooks.stripe.Webhook.construct_event", fake_construct_event)

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "sig_bad"},
    )

    assert response.status_code == 400
