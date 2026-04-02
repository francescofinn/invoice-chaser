from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from constants import (
    FOLLOW_UP_DAYS,
    INVOICE_STATUS_OVERDUE,
    INVOICE_STATUS_SENT,
    INVOICE_STATUS_VIEWED,
)
from database import SessionLocal, settings
from models import EmailLog, Invoice
from services.ai import generate_follow_up_email
from services.email import send_invoice_email
from utils import build_payment_link, calculate_invoice_total, calculate_payment_total

_scheduler: BackgroundScheduler | None = None


def mark_overdue_invoices() -> int:
    db = SessionLocal()
    try:
        today = date.today()
        invoices = db.scalars(
            select(Invoice).where(
                Invoice.status.in_((INVOICE_STATUS_SENT, INVOICE_STATUS_VIEWED)),
                Invoice.due_date < today,
            )
        ).all()
        for invoice in invoices:
            invoice.status = INVOICE_STATUS_OVERDUE
        db.commit()
        return len(invoices)
    finally:
        db.close()


def send_overdue_follow_ups() -> int:
    db = SessionLocal()
    try:
        overdue_invoices = db.scalars(
            select(Invoice)
            .options(
                joinedload(Invoice.client),
                joinedload(Invoice.email_logs),
                joinedload(Invoice.payments),
            )
            .where(Invoice.status == INVOICE_STATUS_OVERDUE)
        ).unique().all()

        sent_count = 0
        for invoice in overdue_invoices:
            days_overdue = (date.today() - invoice.due_date).days
            if days_overdue not in FOLLOW_UP_DAYS:
                continue

            existing_log = next(
                (log for log in invoice.email_logs if log.follow_up_day == days_overdue),
                None,
            )
            if existing_log:
                continue

            invoice_total = calculate_invoice_total(invoice.line_items)
            total_paid = calculate_payment_total(invoice.payments)
            amount_due = invoice_total - total_paid
            if amount_due <= 0:
                continue

            payment_link = build_payment_link(settings.frontend_url, invoice.token)
            content = generate_follow_up_email(
                invoice.client.name,
                invoice.invoice_number,
                str(amount_due),
                invoice.due_date.isoformat(),
                days_overdue,
                payment_link,
                days_overdue,
            )

            log = EmailLog(
                invoice_id=invoice.id,
                subject=content["subject"],
                body=content["body"],
                follow_up_day=days_overdue,
            )
            db.add(log)
            db.flush()

            try:
                send_invoice_email(
                    invoice.client.email,
                    content["subject"],
                    content["body"],
                    payment_link,
                    invoice_number=invoice.invoice_number,
                    amount=str(amount_due),
                    due_date=invoice.due_date.isoformat(),
                    is_overdue=True,
                )
                db.commit()
                sent_count += 1
            except Exception:
                db.rollback()
                raise

        return sent_count
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler

    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(mark_overdue_invoices, "cron", hour=0, minute=0, id="mark-overdue")
    _scheduler.add_job(
        send_overdue_follow_ups,
        "cron",
        hour=9,
        minute=0,
        id="send-follow-ups",
    )
    _scheduler.start()


def stop_scheduler() -> None:
    global _scheduler

    if not _scheduler:
        return

    if _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
