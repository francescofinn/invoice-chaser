from datetime import date, timedelta

from conftest import create_client, create_invoice, create_payment


def test_dashboard_summary_returns_expected_aggregates(client, db_session):
    db_client = create_client(db_session)

    overdue_invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-001",
        status="overdue",
        due_date=date.today() - timedelta(days=10),
        line_items=[{"description": "Strategy", "quantity": "1", "unit_price": "3250.00"}],
    )
    sent_invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-002",
        status="sent",
        due_date=date.today() + timedelta(days=20),
        line_items=[{"description": "Consulting", "quantity": "8", "unit_price": "150.00"}],
    )
    create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-003",
        status="draft",
        due_date=date.today() + timedelta(days=30),
        line_items=[{"description": "Copy", "quantity": "3", "unit_price": "400.00"}],
    )
    create_payment(
        db_session,
        overdue_invoice.id,
        amount="1200.00",
        stripe_payment_intent_id="pi_summary_paid",
    )

    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_outstanding"] == "4450.00"
    assert body["total_overdue"] == "3250.00"
    assert body["total_paid_this_month"] == "1200.00"
    assert body["invoice_count_by_status"]["draft"] == 1
    assert body["invoice_count_by_status"]["sent"] == 1
    assert body["invoice_count_by_status"]["overdue"] == 1
    assert body["cash_flow_forecast"][0]["invoice_ids"] == [sent_invoice.id]
