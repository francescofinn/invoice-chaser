from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from constants import COLLECTION_COMMITMENT_STATUS_ACTIVE, OUTSTANDING_INVOICE_STATUSES
from schemas import CashFlowForecastItem
from utils import calculate_payment_total, calculate_invoice_total, normalize_money


def calculate_remaining_amount(invoice) -> Decimal:
    invoice_total = calculate_invoice_total(invoice.line_items)
    payment_total = calculate_payment_total(getattr(invoice, "payments", []))
    return max(invoice_total - payment_total, Decimal("0.00")).quantize(Decimal("0.01"))


def get_active_commitments(invoice) -> list:
    commitments = getattr(invoice, "collection_commitments", []) or []
    return [
        commitment
        for commitment in commitments
        if commitment.status == COLLECTION_COMMITMENT_STATUS_ACTIVE
    ]


def build_invoice_forecast_entries(invoice, *, active_commitments=None, today: date | None = None) -> list[dict]:
    forecast_start = today or date.today()
    forecast_end = forecast_start + timedelta(days=90)
    commitments = active_commitments if active_commitments is not None else get_active_commitments(invoice)

    if commitments:
        return [
            {
                "date": commitment.due_date,
                "expected_amount": normalize_money(commitment.amount),
                "invoice_ids": [invoice.id],
            }
            for commitment in sorted(commitments, key=lambda item: (item.due_date, item.id))
            if forecast_start <= commitment.due_date <= forecast_end
        ]

    if invoice.status not in OUTSTANDING_INVOICE_STATUSES:
        return []
    if not (forecast_start <= invoice.due_date <= forecast_end):
        return []

    return [
        {
            "date": invoice.due_date,
            "expected_amount": calculate_remaining_amount(invoice),
            "invoice_ids": [invoice.id],
        }
    ]


def build_cash_flow_forecast(invoices, *, today: date | None = None) -> list[CashFlowForecastItem]:
    grouped_forecast: dict[date, dict] = defaultdict(
        lambda: {"expected_amount": Decimal("0.00"), "invoice_ids": []}
    )

    for invoice in invoices:
        for entry in build_invoice_forecast_entries(invoice, today=today):
            grouped_forecast[entry["date"]]["expected_amount"] += entry["expected_amount"]
            for invoice_id in entry["invoice_ids"]:
                if invoice_id not in grouped_forecast[entry["date"]]["invoice_ids"]:
                    grouped_forecast[entry["date"]]["invoice_ids"].append(invoice_id)

    return [
        CashFlowForecastItem(
            date=forecast_date,
            expected_amount=float(values["expected_amount"]),
            invoice_ids=values["invoice_ids"],
        )
        for forecast_date, values in sorted(grouped_forecast.items(), key=lambda item: item[0])
    ]
