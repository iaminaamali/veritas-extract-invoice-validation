from app.schemas import InvoiceRecord
from app.validation import validate_invoice


def make_invoice(**overrides):
    data = {
        "invoice_number": "INV-001", "vendor_name": "Example Vendor",
        "invoice_date": "2026-08-17", "currency": "INR",
        "subtotal": 30000, "tax": 5400, "total": 35400,
    }
    data.update(overrides)
    return InvoiceRecord(**data)


def test_valid_invoice():
    ok, errors = validate_invoice(make_invoice(), "Invoice Date: 17 Aug 2026")
    assert ok
    assert errors == []


def test_total_mismatch_is_rejected():
    ok, errors = validate_invoice(make_invoice(total=35000), "Invoice Date: 17 Aug 2026")
    assert not ok
    assert any("does not match total" in error for error in errors)


def test_date_mismatch_is_rejected():
    ok, errors = validate_invoice(make_invoice(invoice_date="2026-08-18"), "Invoice Date: 17 Aug 2026")
    assert not ok
    assert any("date mismatch" in error for error in errors)


def test_lowercase_currency_is_rejected():
    ok, errors = validate_invoice(make_invoice(currency="inr"), "Invoice Date: 17 Aug 2026")
    assert not ok
    assert any("uppercase" in error for error in errors)
