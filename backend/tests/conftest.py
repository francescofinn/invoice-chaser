import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DB_PATH = Path(tempfile.gettempdir()) / "invoice_chaser_backend_tests.sqlite3"

os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_fixture")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_fixture")
os.environ.setdefault("RESEND_API_KEY", "re_fixture")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-fixture")
os.environ.setdefault("CLERK_SECRET_KEY", "sk_clerk_fixture")
os.environ.setdefault("CLERK_JWKS_URL", "https://example.com/.well-known/jwks.json")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

from database import Base, SessionLocal, engine, get_db
from main import create_app
from models import (
    Client,
    CollectionActivity,
    CollectionCase,
    CollectionCommitment,
    EmailLog,
    Invoice,
    Payment,
)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app(db_session):
    app = create_app(start_scheduler_on_startup=False)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def create_client(
    db_session,
    *,
    name: str = "Alice Johnson",
    email: str = "alice@example.com",
    company: str = "Johnson Design",
) -> Client:
    client = Client(name=name, email=email, company=company)
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


def create_invoice(
    db_session,
    client_id: int,
    *,
    invoice_number: str = "INV-001",
    status: str = "draft",
    issue_date: date | None = None,
    due_date: date | None = None,
    line_items: list[dict] | None = None,
    stripe_payment_intent_id: str | None = None,
) -> Invoice:
    today = date.today()
    invoice = Invoice(
        client_id=client_id,
        invoice_number=invoice_number,
        issue_date=issue_date or today,
        due_date=due_date or today + timedelta(days=30),
        status=status,
        line_items=line_items
        or [{"description": "Design", "quantity": "2", "unit_price": "125.00"}],
        stripe_payment_intent_id=stripe_payment_intent_id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


def create_payment(
    db_session,
    invoice_id: int,
    *,
    amount: str = "100.00",
    stripe_payment_intent_id: str = "pi_paid_123",
) -> Payment:
    payment = Payment(
        invoice_id=invoice_id,
        amount=amount,
        stripe_payment_intent_id=stripe_payment_intent_id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    return payment


def create_email_log(
    db_session,
    invoice_id: int,
    *,
    subject: str = "Reminder",
    body: str = "Please pay",
    follow_up_day: int = 3,
) -> EmailLog:
    email_log = EmailLog(
        invoice_id=invoice_id,
        subject=subject,
        body=body,
        follow_up_day=follow_up_day,
    )
    db_session.add(email_log)
    db_session.commit()
    db_session.refresh(email_log)
    return email_log


def create_collection_case(
    db_session,
    invoice_id: int,
    *,
    status: str = "needs_analysis",
    risk_level: str | None = None,
    risk_summary: str | None = None,
    next_action_key: str | None = None,
    next_action_label: str | None = None,
    next_action_reason: str | None = None,
    draft_subject: str | None = None,
    draft_body: str | None = None,
    last_client_reply: str | None = None,
    last_reply_classification: str | None = None,
    last_contacted_at=None,
    queued_follow_up_date=None,
    last_analyzed_at=None,
) -> CollectionCase:
    collection_case = CollectionCase(
        invoice_id=invoice_id,
        status=status,
        risk_level=risk_level,
        risk_summary=risk_summary,
        next_action_key=next_action_key,
        next_action_label=next_action_label,
        next_action_reason=next_action_reason,
        draft_subject=draft_subject,
        draft_body=draft_body,
        last_client_reply=last_client_reply,
        last_reply_classification=last_reply_classification,
        last_contacted_at=last_contacted_at,
        queued_follow_up_date=queued_follow_up_date,
        last_analyzed_at=last_analyzed_at,
    )
    db_session.add(collection_case)
    db_session.commit()
    db_session.refresh(collection_case)
    return collection_case


def create_collection_commitment(
    db_session,
    invoice_id: int,
    *,
    commitment_type: str = "promise_to_pay",
    due_date=None,
    amount: str = "100.00",
    status: str = "active",
    source: str = "test",
) -> CollectionCommitment:
    commitment = CollectionCommitment(
        invoice_id=invoice_id,
        commitment_type=commitment_type,
        due_date=due_date or date.today() + timedelta(days=7),
        amount=amount,
        status=status,
        source=source,
    )
    db_session.add(commitment)
    db_session.commit()
    db_session.refresh(commitment)
    return commitment


def create_collection_activity(
    db_session,
    invoice_id: int,
    *,
    activity_type: str = "note",
    title: str = "Manual note",
    body: str = "Test activity",
    payload_json: dict | None = None,
) -> CollectionActivity:
    activity = CollectionActivity(
        invoice_id=invoice_id,
        activity_type=activity_type,
        title=title,
        body=body,
        payload_json=payload_json,
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)
    return activity
