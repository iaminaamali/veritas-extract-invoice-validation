# Veritas Extract

Veritas Extract is a small FastAPI service that turns PDF invoices into structured data. The part I actually care about is what happens *after* the model pulls out the fields: the result gets checked against deterministic rules, a failed extraction gets retried with the validation errors fed back in, and anything the system isn't sure about gets flagged for a human to look at.

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

![Architecture diagram](veritas-extract---screenshots/architecture.png)

The idea here isn't to make the LLM responsible for everything. It handles the messy part — reading the invoice and pulling out fields — and the application code takes over for anything that should behave predictably.

## Features

- Extracts invoice fields from text-based PDFs
- Uses OpenAI structured output with a Pydantic schema
- Checks totals, dates, required fields, and currency format
- Retries extraction automatically when validation fails
- Scores confidence with a simple rule-based system
- Sends low-confidence or failed records to human review
- Stores both accepted and review records in PostgreSQL
- Catches duplicate documents using SHA-256 hashes
- Ships with Docker Compose for the API and database
- Has unit tests that don't touch the OpenAI API

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

Copy `.env.example` to `.env` and add your API key.

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

Open `http://127.0.0.1:8000/docs` for the interactive API docs.

![Swagger UI](veritas-extract---screenshots/swaggerui.png)

## Run everything with Docker

Create `.env` first, then run:

```bash
docker compose up --build
```

This spins up both PostgreSQL and the FastAPI service.

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

A successful response includes the extracted invoice, the validation result, a confidence score, how many extraction attempts it took, and the database id.

![Successful extraction result](veritas-extract---screenshots/extraction-result.png)

When confidence comes in below the threshold, the invoice is still saved, but it's marked for review instead of being validated outright:

![Invoice flagged for human review](veritas-extract---screenshots/review-flow.png)

### `GET /review/{invoice_id}`

Returns the stored invoice along with its review information.

### `POST /review/{invoice_id}/approve`

Moves an invoice from `NEEDS_REVIEW` to `VALIDATED`.

## Validation

The validation layer currently checks:

- `subtotal + tax` matches `total` within a small tolerance
- total isn't below subtotal
- invoice number and vendor name are present
- invoice date matches a date found in the source text, when one can be parsed
- currency is uppercase and three characters long

If a model response fails any of these checks, the errors are sent back to the model and it tries again. How many retries it gets is configurable through `MAX_EXTRACTION_ATTEMPTS`.

## Confidence and human review

Confidence here is kept deliberately simple — it's a rule-based heuristic, not a probability the model calculated or that's been calibrated in any way. Missing optional fields lower their own field score, and financial validation errors drag down the financial fields specifically.

Anything below `CONFIDENCE_THRESHOLD` gets marked `NEEDS_REVIEW`. An invoice that runs out of retries is also saved as `NEEDS_REVIEW`, as long as there's a structured result to save.

Here's what the stored data actually looks like in Postgres, including the confidence score and status columns:

![Database record](veritas-extract---screenshots/database.png)

## Tests

Run:

```bash
pytest
```

The suite covers the PDF parser, the validation rules, confidence scoring, and the extraction retry loop. The extraction test uses a fake client, so running it won't spend any API credits.

## Current limitations

This is deliberately a small project, so a few things aren't handled yet:

- Scanned PDFs would need an OCR step first.
- Line items aren't broken out into their own table.
- The confidence score is a heuristic — it hasn't been checked against a labelled dataset.
- Tables are created straight from SQLAlchemy metadata; there's no Alembic migrations yet.
- Uploaded PDFs sit on the local filesystem. A real deployment would want object storage and a retention policy instead.
- No auth, no rate limiting, no production monitoring — all out of scope for now.

## Security

Don't commit `.env`, API keys, real invoices, or customer documents. If a secret ever ends up in a public repo, revoke it and replace it before publishing anything.

## License

MIT License. See `LICENSE`.