import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from database import Base

LINE_ITEMS_TYPE = JSON().with_variant(JSONB(), "postgresql")


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    company = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoices = relationship("Invoice", back_populates="client")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    invoice_number = Column(String, unique=True, nullable=False, index=True)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String, default="draft", nullable=False)
    token = Column(Uuid(as_uuid=True), default=uuid.uuid4, unique=True, index=True, nullable=False)
    line_items = Column(LINE_ITEMS_TYPE, default=list, nullable=False)
    notes = Column(Text, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True)

    client = relationship("Client", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="invoice", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    stripe_payment_intent_id = Column(String, unique=True, nullable=False)
    paid_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoice = relationship("Invoice", back_populates="payments")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    follow_up_day = Column(Integer, nullable=False)

    invoice = relationship("Invoice", back_populates="email_logs")
