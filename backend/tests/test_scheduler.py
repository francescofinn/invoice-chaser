from datetime import date, timedelta

import pytest

from conftest import create_client, create_email_log, create_invoice
from services.scheduler import mark_overdue_invoices, send_overdue_follow_ups


def test_mark_overdue_invoices_updates_only_sent_and_viewed_records(db_session):
    db_client = create_client(db_session)
    sent_invoice = create_invoice(
        db_session,
        db_client.id,
        status="sent",
        due_date=date.today() - timedelta(days=1),
    )
    viewed_invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-002",
        status="viewed",
        due_date=date.today() - timedelta(days=2),
    )
    draft_invoice = create_invoice(
        db_session,
        db_client.id,
        invoice_number="INV-003",
        status="draft",
        due_date=date.today() - timedelta(days=3),
    )

    updated_count = mark_overdue_invoices()
    db_session.expire_all()

    assert updated_count == 2
    assert db_session.get(type(sent_invoice), sent_invoice.id).status == "overdue"
    assert db_session.get(type(viewed_invoice), viewed_invoice.id).status == "overdue"
    assert db_session.get(type(draft_invoice), draft_invoice.id).status == "draft"


def test_send_overdue_follow_ups_sends_only_on_supported_days(db_session, monkeypatch):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        status="overdue",
        due_date=date.today() - timedelta(days=7),
    )

    monkeypatch.setattr(
        "services.scheduler.generate_follow_up_email",
        lambda *args, **kwargs: {"subject": "Invoice overdue", "body": "Please pay"},
    )
    monkeypatch.setattr("services.scheduler.send_invoice_email", lambda *args, **kwargs: "re_123")

    sent_count = send_overdue_follow_ups()
    db_session.expire_all()

    assert sent_count == 1
    refreshed = db_session.get(type(invoice), invoice.id)
    assert len(refreshed.email_logs) == 1
    assert refreshed.email_logs[0].follow_up_day == 7


def test_existing_follow_up_log_suppresses_duplicate_send(db_session, monkeypatch):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        status="overdue",
        due_date=date.today() - timedelta(days=3),
    )
    create_email_log(db_session, invoice.id, follow_up_day=3)

    monkeypatch.setattr(
        "services.scheduler.generate_follow_up_email",
        lambda *args, **kwargs: {"subject": "Invoice overdue", "body": "Please pay"},
    )
    monkeypatch.setattr("services.scheduler.send_invoice_email", lambda *args, **kwargs: "re_123")

    sent_count = send_overdue_follow_ups()
    db_session.expire_all()

    assert sent_count == 0


def test_send_failure_rolls_back_pending_email_log(db_session, monkeypatch):
    db_client = create_client(db_session)
    invoice = create_invoice(
        db_session,
        db_client.id,
        status="overdue",
        due_date=date.today() - timedelta(days=14),
    )

    monkeypatch.setattr(
        "services.scheduler.generate_follow_up_email",
        lambda *args, **kwargs: {"subject": "Urgent invoice", "body": "Please pay"},
    )

    def fake_send(*args, **kwargs):
        raise RuntimeError("Resend unavailable")

    monkeypatch.setattr("services.scheduler.send_invoice_email", fake_send)

    with pytest.raises(RuntimeError):
        send_overdue_follow_ups()
    db_session.expire_all()

    refreshed = db_session.get(type(invoice), invoice.id)
    assert len(refreshed.email_logs) == 0
