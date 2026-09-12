import fitz
import pytest

from app.pdf_parser import extract_text_from_pdf


def test_extract_text_from_pdf(tmp_path):
    path = tmp_path / "invoice.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Invoice No: INV-001")
    doc.save(path)
    doc.close()

    text = extract_text_from_pdf(path)
    assert "INV-001" in text


def test_scanned_or_empty_pdf_is_rejected(tmp_path):
    path = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()

    with pytest.raises(ValueError, match="no extractable text"):
        extract_text_from_pdf(path)
