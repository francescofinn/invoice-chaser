from datetime import date, datetime
from decimal import Decimal
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from constants import INVOICE_STATUS_DRAFT
from utils import calculate_invoice_total, serialize_line_items, validate_invoice_status


class LineItem(BaseModel):
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)


class ClientCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    company: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    email: str | None = Field(default=None, min_length=1)
    company: str | None = None


class ClientResponse(ClientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class InvoiceCreate(BaseModel):
    client_id: int
    invoice_number: str = Field(min_length=1)
    issue_date: date
    due_date: date
    line_items: list[LineItem] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.due_date < self.issue_date:
            raise ValueError("due_date must be on or after issue_date")
        return self


class InvoiceUpdate(BaseModel):
    due_date: date | None = None
    status: str | None = None
    line_items: list[LineItem] | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_invoice_status(value)


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    invoice_number: str
    issue_date: date
    due_date: date
    status: str = INVOICE_STATUS_DRAFT
    token: uuid.UUID
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    notes: str | None = None
    client: ClientResponse

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return validate_invoice_status(value)

    @field_validator("line_items", mode="before")
    @classmethod
    def normalize_line_items(cls, value: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        return serialize_line_items(value or [])

    @computed_field
    @property
    def total(self) -> Decimal:
        return calculate_invoice_total(self.line_items)


class PublicInvoiceResponse(InvoiceResponse):
    stripe_client_secret: str


class CashFlowForecastItem(BaseModel):
    date: date
    expected_amount: float
    invoice_ids: list[int]


class DashboardSummary(BaseModel):
    total_outstanding: Decimal
    total_overdue: Decimal
    total_paid_this_month: Decimal
    invoice_count_by_status: dict[str, int]
    cash_flow_forecast: list[CashFlowForecastItem]
