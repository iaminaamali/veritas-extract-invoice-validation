from datetime import datetime

from app.schemas import InvoiceRecord


def extract_date_from_text(invoice_text: str) -> str | None:
    for line in invoice_text.splitlines():
        if "Date:" not in line or "Due Date:" in line:
            continue
        date_text = line.split("Date:", 1)[1].strip()
        if "Due Date:" in date_text:
            date_text = date_text.split("Due Date:", 1)[0].strip()
        for fmt in (
            "%d %b %Y",
            "%d %B %Y",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
        ):
            try:
                return datetime.strptime(date_text, fmt).date().isoformat()
            except ValueError:
                continue
    return None


def validate_invoice(invoice: InvoiceRecord, invoice_text: str) -> tuple[bool, list[str]]:
    errors: list[str] = []
    tax = invoice.tax or 0.0

    if abs((invoice.subtotal + tax) - invoice.total) > 0.01:
        errors.append(
            f"Subtotal + tax ({invoice.subtotal + tax:.2f}) does not match total ({invoice.total:.2f})"
        )

    if invoice.total < invoice.subtotal:
        errors.append("Total cannot be smaller than subtotal")

    if not invoice.invoice_number.strip():
        errors.append("Invoice number is empty")
    if not invoice.vendor_name.strip():
        errors.append("Vendor name is empty")

    source_date = extract_date_from_text(invoice_text)
    if source_date and invoice.invoice_date.isoformat() != source_date:
        errors.append(
            f"Invoice date mismatch: extracted '{invoice.invoice_date.isoformat()}', source '{source_date}'"
        )

    if invoice.currency != invoice.currency.upper():
        errors.append("Currency must use an uppercase ISO-style code")

    return not errors, errors
