from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from schemas import ClientResponse, InvoiceResponse
from utils import build_payment_link, calculate_invoice_total


def test_calculate_invoice_total_uses_decimal_string_conversion():
    total = calculate_invoice_total(
        [
            {"description": "Strategy", "quantity": 1, "unit_price": 2500.00},
            {"description": "Design", "quantity": "2", "unit_price": "125.50"},
        ]
    )

    assert total == Decimal("2751.00")


def test_invoice_response_computes_total_from_line_items():
    invoice = InvoiceResponse(
        id=1,
        client_id=1,
        invoice_number="INV-001",
        issue_date=date(2026, 4, 1),
        due_date=date(2026, 4, 30),
        status="draft",
        token=uuid4(),
        line_items=[
            {"description": "Strategy", "quantity": "1", "unit_price": "2500.00"},
            {"description": "Design", "quantity": "2", "unit_price": "125.50"},
        ],
        notes=None,
        client=ClientResponse(
            id=1,
            name="Alice Johnson",
            email="alice@example.com",
            company="Johnson Design",
            created_at=datetime(2026, 4, 1, 12, 0, 0),
        ),
    )

    assert invoice.total == Decimal("2751.00")
    assert invoice.line_items[0]["quantity"] == "1"
    assert invoice.line_items[0]["unit_price"] == "2500.00"


def test_build_payment_link_avoids_double_slashes():
    link = build_payment_link("http://localhost:5173/", uuid4())

    assert link.startswith("http://localhost:5173/pay/")
