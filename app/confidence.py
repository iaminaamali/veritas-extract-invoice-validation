from app.config import CONFIDENCE_THRESHOLD
from app.schemas import InvoiceRecord


def calculate_field_confidence(invoice: InvoiceRecord, validation_errors: list[str]) -> dict[str, float]:
    confidence = {
        "invoice_number": 1.0,
        "vendor_name": 1.0,
        "invoice_date": 1.0,
        "currency": 1.0,
        "subtotal": 1.0,
        "tax": 1.0,
        "total": 1.0,
        "payment_terms": 1.0,
        "purchase_order_number": 1.0,
    }

    if invoice.tax is None:
        confidence["tax"] = 0.5
    if invoice.payment_terms is None:
        confidence["payment_terms"] = 0.5
    if invoice.purchase_order_number is None:
        confidence["purchase_order_number"] = 0.5

    if validation_errors:
        for field in ("subtotal", "tax", "total"):
            confidence[field] *= 0.7

    return confidence


def calculate_record_confidence(field_confidence: dict[str, float]) -> float:
    total_confidence = field_confidence["total"]
    other = [v for k, v in field_confidence.items() if k != "total"]
    return (total_confidence * 2 + sum(other)) / (2 + len(other))
