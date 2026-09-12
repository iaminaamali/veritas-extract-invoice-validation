from pathlib import Path

import fitz


def extract_text_from_pdf(file_path: str | Path) -> str:
    try:
        document = fitz.open(file_path)
    except Exception as exc:
        raise ValueError("The uploaded file is not a readable PDF.") from exc

    try:
        pages = [page.get_text("text") for page in document]
    finally:
        document.close()

    full_text = "\n".join(pages).strip()
    if not full_text:
        raise ValueError(
            "PDF contains no extractable text. It may be scanned and require OCR."
        )
    return full_text
