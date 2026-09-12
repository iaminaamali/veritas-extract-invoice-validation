from datetime import date

from pydantic import BaseModel, Field


class InvoiceRecord(BaseModel):
    invoice_number: str = Field(min_length=1)
    vendor_name: str = Field(min_length=1)
    invoice_date: date
    currency: str = Field(min_length=3, max_length=3)
    subtotal: float = Field(ge=0)
    tax: float | None = Field(default=None, ge=0)
    total: float = Field(ge=0)
    payment_terms: str | None = None
    purchase_order_number: str | None = None


class ExtractionResponse(BaseModel):
    filename: str | None = None
    success: bool
    saved: bool = False
    database_id: int | None = None
    review_required: bool = False
    duplicate: bool = False
    message: str | None = None
    reason: str | None = None
    invoice: InvoiceRecord | None = None
    attempts: int | None = None
    errors: list[str] = Field(default_factory=list)
    field_confidence: dict[str, float] | None = None
    confidence: float | None = None
    threshold: float | None = None
    review: dict | None = None
