# Veritas Extract

Veritas Extract is a small FastAPI service for turning PDF invoices into structured records. The interesting part is what happens after the model extracts the fields: the result is checked with deterministic rules, failed extractions are retried with the validation errors as feedback, and uncertain records can be sent for human approval.

## What it does

```text
PDF
 │
 ▼
PyMuPDF text extraction
 │
 ▼
OpenAI structured output
 │
 ▼
Pydantic schema
 │
 ▼
Deterministic validation
 │
 ├── valid ──────────────┐
 │                        │
 └── invalid → retry ─────┘
          │
          ▼
Rule-based confidence
          │
     ┌────┴────┐
     ▼         ▼
 VALIDATED  NEEDS_REVIEW
     │         │
     └────┬────┘
          ▼
      PostgreSQL
```

The goal is not to make the LLM do everything. The model handles the messy extraction step, while application code handles checks that should be predictable.

## Features

- Extracts invoice fields from text-based PDFs
- Uses OpenAI structured output with a Pydantic schema
- Checks totals, dates, required fields, and currency format
- Retries an extraction when deterministic validation fails
- Calculates a simple rule-based confidence score
- Routes low-confidence/failed records to human review
- Stores accepted and review records in PostgreSQL
- Detects duplicate documents with SHA-256 hashes
- Includes Docker Compose for the API and PostgreSQL
- Includes unit tests that do not call the OpenAI API

## Project structure

```text
veritas-extract/
├── app/
│   ├── confidence.py      # Rule-based confidence scoring
│   ├── config.py          # Environment configuration
│   ├── database.py        # SQLAlchemy engine and persistence
│   ├── extraction.py      # LLM extraction + retry loop
│   ├── main.py            # FastAPI routes
│   ├── models.py          # PostgreSQL/SQLAlchemy model
│   ├── pdf_parser.py      # PDF text extraction
│   ├── review.py          # Human-review response data
│   ├── schemas.py         # Pydantic models
│   └── validation.py      # Deterministic invoice checks
├── tests/
│   ├── test_confidence.py
│   ├── test_extraction.py
│   ├── test_pdf_parser.py
│   └── test_validation.py
├── samples/               # Put sanitized local test invoices here
├── uploads/               # Runtime uploads; ignored by git
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── LICENSE
├── pytest.ini
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.12+
- Docker Desktop / Docker Engine
- An OpenAI API key

## Run locally

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the environment

Copy `.env.example` to `.env` and set your API key.

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

`.env` is ignored by git. Never put a real API key in source code.

### 4. Start PostgreSQL

```bash
docker compose up -d db
```

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

## Run everything with Docker

Create `.env` first, then run:

```bash
docker compose up --build
```

This starts both PostgreSQL and the FastAPI service.

## API

### `GET /health`

Basic service health check.

### `POST /extract`

Upload a PDF invoice as multipart form data.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/extract" \
  -H "accept: application/json" \
  -F "file=@samples/invoice.pdf"
```

A successful response contains the extracted invoice, validation result, confidence score, number of extraction attempts, and database id.

### `GET /review/{invoice_id}`

Returns the stored invoice and its review information.

### `POST /review/{invoice_id}/approve`

Moves an invoice from `NEEDS_REVIEW` to `VALIDATED`.

## Validation

The current validation layer checks:

- `subtotal + tax` matches `total` within a small tolerance
- total is not below subtotal
- invoice number and vendor name are present
- invoice date agrees with a date found in the source text when it can be parsed
- currency is uppercase and three characters long

If a model response fails these checks, the validation errors are sent back to the model and the invoice is extracted again. The retry count is configurable through `MAX_EXTRACTION_ATTEMPTS`.

## Confidence and human review

Confidence in this project is intentionally simple. It is a **rule-based heuristic**, not a probability produced or calibrated by the model. Missing optional fields lower their field score, and financial validation errors lower the financial field scores.

Records below `CONFIDENCE_THRESHOLD` are marked `NEEDS_REVIEW`. A record that exhausts the extraction retries is also persisted as `NEEDS_REVIEW` when a structured result is available.

## Tests

Run:

```bash
pytest
```

The test suite covers the PDF parser, validation rules, confidence scoring, and the extraction retry loop. The extraction test uses a fake client, so running the tests does not spend API credits.

## Current limitations

This version deliberately stays small. A few things are not implemented yet:

- Scanned PDFs need an OCR step.
- Line items are not extracted into a separate table.
- The confidence score is heuristic and has not been calibrated against a labelled dataset.
- Database tables are created from SQLAlchemy metadata; there are no Alembic migrations yet.
- Uploaded PDFs are stored on the local filesystem. A hosted deployment would normally use object storage and a retention policy.
- Authentication, rate limiting, and production monitoring are outside the current scope.

## Security

Do not commit `.env`, API keys, real invoices, or customer documents. If a secret has ever been committed to a public repository, revoke it and replace it before publishing the repository.

## License

MIT License. See `LICENSE`.
