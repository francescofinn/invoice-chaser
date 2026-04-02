from conftest import create_client, create_invoice


def test_create_list_filter_get_update_and_delete_invoice(client, db_session):
    db_client = create_client(db_session)

    create_response = client.post(
        "/invoices",
        json={
            "client_id": db_client.id,
            "invoice_number": "INV-001",
            "issue_date": "2026-04-01",
            "due_date": "2026-04-30",
            "line_items": [
                {"description": "Strategy", "quantity": "1", "unit_price": "2500.00"}
            ],
            "notes": "Net 30",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["invoice_number"] == "INV-001"
    assert created["client"]["id"] == db_client.id
    assert created["total"] == "2500.00"

    list_response = client.get("/invoices")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    filter_response = client.get("/invoices", params={"status": "draft"})
    assert filter_response.status_code == 200
    assert len(filter_response.json()) == 1

    get_response = client.get(f"/invoices/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["notes"] == "Net 30"

    update_response = client.put(
        f"/invoices/{created['id']}",
        json={
            "status": "sent",
            "notes": "Updated note",
            "line_items": [
                {"description": "Strategy", "quantity": "2", "unit_price": "1250.00"}
            ],
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "sent"
    assert update_response.json()["total"] == "2500.00"

    delete_response = client.delete(f"/invoices/{created['id']}")
    assert delete_response.status_code == 409


def test_delete_draft_invoice_succeeds(client, db_session):
    db_client = create_client(db_session)
    invoice = create_invoice(db_session, db_client.id, status="draft")

    response = client.delete(f"/invoices/{invoice.id}")

    assert response.status_code == 204


def test_send_invoice_from_draft_creates_payment_intent_logs_email_and_marks_sent(
    client,
    db_session,
    monkeypatch,
):
    db_client = create_client(db_session)
    invoice = create_invoice(db_session, db_client.id, status="draft")

    def fake_payment_intent_create(**kwargs):
        assert kwargs["currency"] == "usd"
        assert kwargs["metadata"]["invoice_id"] == str(invoice.id)
        return {"id": "pi_123", "client_secret": "pi_123_secret"}

    monkeypatch.setattr("routers.invoices.stripe.PaymentIntent.create", fake_payment_intent_create)
    monkeypatch.setattr("routers.invoices.send_invoice_email", lambda *args, **kwargs: "re_123")

    response = client.post(f"/invoices/{invoice.id}/send")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sent"

    refreshed = db_session.get(type(invoice), invoice.id)
    assert refreshed.stripe_payment_intent_id == "pi_123"
    assert refreshed.status == "sent"
    assert len(refreshed.email_logs) == 1
    assert refreshed.email_logs[0].follow_up_day == 0


def test_send_invoice_from_non_draft_is_rejected(client, db_session):
    db_client = create_client(db_session)
    invoice = create_invoice(db_session, db_client.id, status="sent")

    response = client.post(f"/invoices/{invoice.id}/send")

    assert response.status_code == 409


def test_public_invoice_reuses_existing_non_cancelled_payment_intent(
    client,
    db_session,
    monkeypatch,
):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        status="sent",
        stripe_payment_intent_id="pi_existing",
    )

    monkeypatch.setattr(
        "routers.invoices.stripe.PaymentIntent.retrieve",
        lambda intent_id: {
            "id": intent_id,
            "status": "requires_payment_method",
            "client_secret": "pi_existing_secret",
        },
    )

    response = client.get(f"/invoices/public/{invoice.token}")

    assert response.status_code == 200
    body = response.json()
    assert body["stripe_client_secret"] == "pi_existing_secret"
    assert body["status"] == "viewed"


def test_public_invoice_creates_new_payment_intent_when_missing_or_cancelled(
    client,
    db_session,
    monkeypatch,
):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        status="sent",
        stripe_payment_intent_id="pi_cancelled",
    )

    monkeypatch.setattr(
        "routers.invoices.stripe.PaymentIntent.retrieve",
        lambda intent_id: {
            "id": intent_id,
            "status": "cancelled",
            "client_secret": "pi_cancelled_secret",
        },
    )
    monkeypatch.setattr(
        "routers.invoices.stripe.PaymentIntent.create",
        lambda **kwargs: {"id": "pi_new", "client_secret": "pi_new_secret"},
    )

    response = client.get(f"/invoices/public/{invoice.token}")

    assert response.status_code == 200
    assert response.json()["stripe_client_secret"] == "pi_new_secret"

    refreshed = db_session.get(type(invoice), invoice.id)
    assert refreshed.stripe_payment_intent_id == "pi_new"


def test_invalid_public_invoice_token_returns_404(client):
    response = client.get("/invoices/public/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_invoice_responses_normalize_numeric_line_items_to_frontend_shape(client, db_session):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        line_items=[{"description": "Strategy", "quantity": 2, "unit_price": 1250.0}],
    )

    response = client.get(f"/invoices/{invoice.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["line_items"] == [
        {"description": "Strategy", "quantity": "2", "unit_price": "1250.0"}
    ]
