from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from constants import OUTSTANDING_INVOICE_STATUSES
from database import get_db
from models import Invoice, Payment
from schemas import DashboardSummary
from services.collections import build_cash_flow_forecast, calculate_remaining_amount

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    today = date.today()
    ninety_days_out = today + timedelta(days=90)

    outstanding_invoices = db.scalars(
        select(Invoice)
        .options(joinedload(Invoice.payments), selectinload(Invoice.collection_commitments))
        .where(Invoice.status.in_(OUTSTANDING_INVOICE_STATUSES))
    ).unique().all()

    total_outstanding = sum(
        (calculate_remaining_amount(invoice) for invoice in outstanding_invoices),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    total_overdue = sum(
        (calculate_remaining_amount(invoice) for invoice in outstanding_invoices if invoice.due_date < today),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))

    start_of_month = today.replace(day=1)
    total_paid_this_month = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.paid_at >= start_of_month)
    )
    total_paid_this_month = Decimal(str(total_paid_this_month or 0)).quantize(Decimal("0.01"))

    status_counts = dict(
        db.execute(select(Invoice.status, func.count(Invoice.id)).group_by(Invoice.status)).all()
    )

    forecast_rows = [
        invoice
        for invoice in outstanding_invoices
        if invoice.due_date <= ninety_days_out or invoice.collection_commitments
    ]
    cash_flow_forecast = build_cash_flow_forecast(forecast_rows, today=today)

    return DashboardSummary(
        total_outstanding=total_outstanding,
        total_overdue=total_overdue,
        total_paid_this_month=total_paid_this_month,
        invoice_count_by_status=status_counts,
        cash_flow_forecast=cash_flow_forecast,
    )
