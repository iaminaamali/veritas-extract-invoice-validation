from types import SimpleNamespace

import app.extraction as extraction
from app.schemas import InvoiceRecord


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0

    def parse(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(output_parsed=next(self.outputs))


class FakeClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


def invoice(total):
    return InvoiceRecord(
        invoice_number="INV-001", vendor_name="Vendor", invoice_date="2026-08-17",
        currency="INR", subtotal=100, tax=10, total=total,
    )


def test_extraction_retries_after_validation_failure(monkeypatch):
    client = FakeClient([invoice(105), invoice(110)])
    monkeypatch.setattr(extraction, "_get_client", lambda: client)

    result = extraction.extract_invoice("Invoice Date: 17 Aug 2026")

    assert result["success"] is True
    assert result["attempts"] == 2
    assert client.responses.calls == 2
