# Statement Extractor

Multi-tenant SaaS that extracts transactions from Canadian bank and card
statements (PDF, scanned, or photographed) into a structured, editable
table — CSV/XLSX export included.

No generative AI / LLM API is used in the extraction pipeline. Extraction
relies on deterministic PDF parsing for text-based PDFs, Tesseract OCR for
scanned documents, and classical ML (scikit-learn / CRF, not transformer
models) for institution/layout classification and debit-credit
disambiguation on ambiguous statements. See `docs/architecture.md` for the
full reasoning, including why a human review step is required to reach
real-world "100% correct" — no automated pipeline gets there alone.

## Structure

```
backend/    FastAPI app, PostgreSQL via SQLAlchemy + Alembic, Celery workers
frontend/   React + TypeScript + Vite + Tailwind
deploy/     systemd unit files + Nginx config (no Docker)
docs/       architecture and design decisions
```

## Local development

### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL etc.
# requires local Postgres + Redis running
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Deployment

No Docker/containers — deploys as plain systemd services behind Nginx on a
standard Ubuntu VPS. See `deploy/` for unit files and reverse-proxy config,
and `docs/architecture.md` for the deployment trade-offs of this approach.

## Status

Early skeleton — see `docs/architecture.md` for the roadmap. Most API
endpoints and the extraction pipeline are stubbed with `TODO`s marking the
next implementation steps.
