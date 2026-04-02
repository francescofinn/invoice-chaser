from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping

from constants import INVOICE_STATUSES

MONEY_QUANTUM = Decimal("0.01")
CENTS_MULTIPLIER = Decimal("100")


def normalize_money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_invoice_total(line_items: Iterable[Mapping] | None) -> Decimal:
    if not line_items:
        return Decimal("0.00")

    total = Decimal("0.00")
    for item in line_items:
        quantity = Decimal(str(item["quantity"]))
        unit_price = Decimal(str(item["unit_price"]))
        total += quantity * unit_price

    return total.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_payment_total(payments: Iterable) -> Decimal:
    total = Decimal("0.00")
    for payment in payments:
        total += Decimal(str(payment.amount))
    return total.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def decimal_to_cents(value: Decimal | int | float | str) -> int:
    normalized = normalize_money(value)
    cents = (normalized * CENTS_MULTIPLIER).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def build_payment_link(frontend_url: str, token) -> str:
    return f"{frontend_url.rstrip('/')}/pay/{token}"


def normalize_line_item(item: Mapping) -> dict:
    return {
        "description": item["description"],
        "quantity": str(item["quantity"]),
        "unit_price": str(item["unit_price"]),
    }


def serialize_line_items(line_items: Iterable) -> list[dict]:
    serialized: list[dict] = []
    for item in line_items:
        if hasattr(item, "model_dump"):
            serialized.append(item.model_dump(mode="json"))
            continue

        serialized.append(normalize_line_item(item))
    return serialized


def validate_invoice_status(status: str) -> str:
    if status not in INVOICE_STATUSES:
        raise ValueError(f"Unsupported invoice status: {status}")
    return status
