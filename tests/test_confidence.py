from app.confidence import calculate_field_confidence, calculate_record_confidence
from app.schemas import InvoiceRecord


def test_missing_optional_fields_reduce_confidence():
    invoice = InvoiceRecord(
        invoice_number="INV-001", vendor_name="Vendor", invoice_date="2026-08-17",
        currency="INR", subtotal=100, tax=None, total=100,
    )
    fields = calculate_field_confidence(invoice, [])
    assert fields["tax"] == 0.5
    assert calculate_record_confidence(fields) < 1.0


def test_validation_errors_reduce_financial_confidence():
    invoice = InvoiceRecord(
        invoice_number="INV-001", vendor_name="Vendor", invoice_date="2026-08-17",
        currency="INR", subtotal=100, tax=10, total=110,
    )
    fields = calculate_field_confidence(invoice, ["total mismatch"])
    assert fields["total"] == 0.7
