import hashlib
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.confidence import calculate_field_confidence, calculate_record_confidence
from app.config import CONFIDENCE_THRESHOLD, MAX_FILE_SIZE_MB, UPLOAD_DIR
from app.database import (
    approve_invoice_review,
    create_tables,
    get_invoice_by_hash,
    get_invoice_by_id,
    save_invoice,
)
from app.extraction import extract_invoice
from app.pdf_parser import extract_text_from_pdf
from app.schemas import ExtractionResponse, InvoiceRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Veritas Extract",
    description="Invoice extraction, validation, and human review API.",
    version="1.0.0",
)
UPLOAD_DIR = Path(UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
def startup() -> None:
    create_tables()


@app.get("/health")
def health():
    return {"status": "ok", "service": "veritas-extract"}


@app.post("/extract", response_model=ExtractionResponse)
async def extract_invoice_endpoint(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_FILE_SIZE_MB} MB limit.",
        )

    file_hash = hashlib.sha256(content).hexdigest()
    existing_invoice = get_invoice_by_hash(file_hash)
    if existing_invoice:
        return {
            "filename": file.filename,
            "success": False,
            "duplicate": True,
            "message": "This document has already been processed.",
            "database_id": existing_invoice.id,
        }

    file_path = UPLOAD_DIR / f"{file_hash}.pdf"
    file_path.write_bytes(content)

    try:
        extracted_text = extract_text_from_pdf(file_path)
        extraction_result = extract_invoice(extracted_text)
    except ValueError as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        logger.exception("Invoice extraction failed")
        raise HTTPException(status_code=502, detail="Invoice extraction service failed.") from exc

    if not extraction_result["success"]:
        review = extraction_result["review"]
        invoice_data = review["invoice"]
        if invoice_data is None:
            file_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=422,
                detail="The model could not produce a reviewable invoice record.",
            )

        invoice = InvoiceRecord.model_validate(invoice_data)
        database_id = save_invoice(
            invoice=invoice,
            file_hash=file_hash,
            status="NEEDS_REVIEW",
            confidence=0.0,
            attempts=review["attempts"],
            validation_errors=review["validation_errors"],
        )
        return {
            "filename": file.filename,
            "success": False,
            "review_required": True,
            "saved": True,
            "database_id": database_id,
            "review": review,
        }

    invoice = extraction_result["invoice"]
    field_confidence = calculate_field_confidence(invoice, extraction_result["errors"])
    record_confidence = calculate_record_confidence(field_confidence)
    status = "VALIDATED" if record_confidence >= CONFIDENCE_THRESHOLD else "NEEDS_REVIEW"

    database_id = save_invoice(
        invoice=invoice,
        file_hash=file_hash,
        status=status,
        confidence=record_confidence,
        attempts=extraction_result["attempts"],
        validation_errors=extraction_result["errors"],
    )

    return {
        "filename": file.filename,
        "success": status == "VALIDATED",
        "saved": True,
        "review_required": status == "NEEDS_REVIEW",
        "reason": "Confidence below threshold" if status == "NEEDS_REVIEW" else None,
        "database_id": database_id,
        "invoice": invoice,
        "attempts": extraction_result["attempts"],
        "errors": extraction_result["errors"],
        "field_confidence": field_confidence,
        "confidence": record_confidence,
        "threshold": CONFIDENCE_THRESHOLD,
    }


@app.get("/review/{invoice_id}")
def get_review(invoice_id: int):
    invoice = get_invoice_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "success": True,
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "vendor_name": invoice.vendor_name,
            "invoice_date": invoice.invoice_date,
            "currency": invoice.currency,
            "subtotal": invoice.subtotal,
            "tax": invoice.tax,
            "total": invoice.total,
            "payment_terms": invoice.payment_terms,
            "purchase_order_number": invoice.purchase_order_number,
            "confidence": float(invoice.confidence) if invoice.confidence is not None else None,
            "status": invoice.status,
            "attempts": invoice.attempts,
            "validation_errors": invoice.validation_errors,
        },
    }


@app.post("/review/{invoice_id}/approve")
def approve_review(invoice_id: int):
    invoice = approve_invoice_review(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {
        "success": True,
        "message": "Invoice approved.",
        "database_id": invoice.id,
        "status": invoice.status,
    }
