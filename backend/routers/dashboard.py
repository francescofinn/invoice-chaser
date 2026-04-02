from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from constants import OUTSTANDING_INVOICE_STATUSES
from database import get_db
from models import Invoice, Payment
from schemas import CashFlowForecastItem, DashboardSummary
from utils import calculate_invoice_total

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    today = date.today()
    ninety_days_out = today + timedelta(days=90)

    outstanding_invoices = db.scalars(
        select(Invoice)
        .options(joinedload(Invoice.payments))
        .where(Invoice.status.in_(OUTSTANDING_INVOICE_STATUSES))
    ).unique().all()

    total_outstanding = sum(
        (calculate_invoice_total(invoice.line_items) for invoice in outstanding_invoices),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    total_overdue = sum(
        (
            calculate_invoice_total(invoice.line_items)
            for invoice in outstanding_invoices
            if invoice.due_date < today
        ),
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

    forecast_rows = db.scalars(
        select(Invoice).where(
            Invoice.status.in_(("sent", "viewed", "partially_paid")),
            Invoice.due_date >= today,
            Invoice.due_date <= ninety_days_out,
        )
    ).all()

    grouped_forecast: dict[date, dict] = defaultdict(lambda: {"expected_amount": Decimal("0.00"), "invoice_ids": []})
    for invoice in forecast_rows:
        forecast_entry = grouped_forecast[invoice.due_date]
        forecast_entry["expected_amount"] += calculate_invoice_total(invoice.line_items)
        forecast_entry["invoice_ids"].append(invoice.id)

    cash_flow_forecast = [
        CashFlowForecastItem(
            date=forecast_date,
            expected_amount=float(values["expected_amount"]),
            invoice_ids=values["invoice_ids"],
        )
        for forecast_date, values in sorted(grouped_forecast.items(), key=lambda item: item[0])
    ]

    return DashboardSummary(
        total_outstanding=total_outstanding,
        total_overdue=total_overdue,
        total_paid_this_month=total_paid_this_month,
        invoice_count_by_status=status_counts,
        cash_flow_forecast=cash_flow_forecast,
    )
