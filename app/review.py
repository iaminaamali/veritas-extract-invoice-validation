from uuid import uuid4


def create_review_item(invoice, attempts: int, validation_errors: list[str], confidence=None):
    return {
        "review_id": f"REV-{uuid4().hex[:8].upper()}",
        "status": "NEEDS_REVIEW",
        "attempts": attempts,
        "reason": "Extraction did not pass deterministic validation",
        "invoice": invoice.model_dump(mode="json") if invoice is not None else None,
        "validation_errors": validation_errors,
        "confidence": confidence,
    }
