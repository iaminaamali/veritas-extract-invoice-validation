import logging

from openai import OpenAI

from app.config import MAX_EXTRACTION_ATTEMPTS, OPENAI_API_KEY, OPENAI_MODEL
from app.review import create_review_item
from app.schemas import InvoiceRecord
from app.validation import validate_invoice

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=OPENAI_API_KEY)


def extract_invoice(invoice_text: str):
    client = _get_client()
    messages = [
        {
            "role": "system",
            "content": (
                "Extract invoice information from the provided invoice text. "
                "Only use information supported by the invoice. Do not invent values."
            ),
        },
        {"role": "user", "content": invoice_text},
    ]

    invoice = None
    validation_errors: list[str] = []

    for attempt in range(1, MAX_EXTRACTION_ATTEMPTS + 1):
        logger.info("Extraction attempt %s/%s", attempt, MAX_EXTRACTION_ATTEMPTS)
        response = client.responses.parse(
            model=OPENAI_MODEL,
            input=messages,
            text_format=InvoiceRecord,
        )
        invoice = response.output_parsed

        if invoice is None:
            validation_errors = ["The model returned no structured invoice output"]
        else:
            is_valid, validation_errors = validate_invoice(invoice, invoice_text)
            if is_valid:
                return {
                    "success": True,
                    "invoice": invoice,
                    "attempts": attempt,
                    "errors": [],
                }

        messages.append(
            {
                "role": "assistant",
                "content": invoice.model_dump_json() if invoice else "No structured output returned.",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "The previous extraction failed deterministic validation.\n"
                    + "\n".join(f"- {error}" for error in validation_errors)
                    + "\nRe-read the original invoice text and return a corrected invoice."
                ),
            }
        )

    return {
        "success": False,
        "review_required": True,
        "review": create_review_item(
            invoice=invoice,
            attempts=MAX_EXTRACTION_ATTEMPTS,
            validation_errors=validation_errors,
        ),
    }
