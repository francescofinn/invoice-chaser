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
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

from database import Base, SessionLocal, engine, get_db
from main import create_app
from models import Client, EmailLog, Invoice, Payment


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
