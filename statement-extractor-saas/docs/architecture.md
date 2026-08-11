# Architecture

## What this is

A multi-tenant SaaS for accountants/businesses to upload Canadian bank and
card statements (PDF, scanned, or photographed) and get back a structured,
reviewed transaction table — extending the extraction rules originally
built as a Claude Skill (`canadian-bank-statement-extractor`) into a real
product.

## The core constraint: no generative AI, classical ML only

The extraction pipeline never calls a generative/LLM API (no OpenAI,
Claude, etc.) to read or interpret statement content. It uses:

- **Deterministic parsing** (PyMuPDF/pdfplumber) for PDFs with a real text
  layer — this is the majority case for real statements and the highest-
  accuracy path, since it's just reading text that's already there.
- **Tesseract OCR** (open-source, no per-page API cost) + OpenCV
  preprocessing for scanned/photographed statements.
- **Classical, trained-in-house ML** (scikit-learn linear models, CRF
  sequence tagging) for institution/layout classification and debit/credit
  disambiguation on ambiguous cases — trained on our own labeled data, not
  a third-party model.

Stripe (for billing) is a deliberate exception — it's an external API, but
it's unrelated to the extraction pipeline and to the "no AI" constraint.

### On "100% correct"

No automated pipeline — ML, rule-based, or LLM-based — reaches 100% on
arbitrary real-world statements. The product's actual path to 100% is:
very high automated accuracy on known formats (95–99%+) **plus a mandatory
human review step** before data is finalized, with every correction fed
back as labeled training data (`ml_training_samples` table). This is the
same pattern used by Plaid/Ramp/Expensify-style data-extraction products.
Skipping the review step and presenting automated output as final is the
single biggest risk to the "100% correct" promise — don't cut it, even
under pressure to ship faster.

## Architecture style

**Modular monolith**, not microservices. At current team size and stage,
splitting into services adds distributed-systems failure modes (partial
failures, network hops, data consistency across services) without a
corresponding benefit. Internal module boundaries
(`ingestion/`, `extraction/`, `ml/`, API routers) are kept clean so a
future split — if genuinely justified by scale or team size — is
tractable rather than a rewrite.

## Stack and why

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + TypeScript + Vite + Tailwind | Matches existing (Arwa) stack; fast dev loop |
| Backend | FastAPI (Python), async | Specified by the founder; strong fit for I/O-heavy upload/OCR workloads |
| Database | PostgreSQL | ACID for financial data; JSONB for flexible per-template metadata; mature Row-Level Security support for multi-tenancy |
| Background jobs | Redis + Celery, native install | OCR/ML extraction takes seconds-to-minutes — must not block HTTP requests. Both install as plain packages/systemd services, no container needed |
| OCR | Tesseract + OpenCV | Open-source, no API, no per-page cost — matters at high volume |
| PDF text extraction | PyMuPDF + pdfplumber | Deterministic, no ML needed for the majority (text-based) case |
| Classical ML | scikit-learn + sklearn-crfsuite | Trained in-house, not a paid/generative API |
| Auth | JWT (short access + longer refresh), bcrypt | No Firebase Auth |
| Storage | Local disk on VPS, encrypted at rest, off-box backups | No Firestore/S3 dependency at this stage |
| Deployment | Ubuntu VPS + Nginx + systemd | No Docker/containers, per founder's explicit constraint; matches the existing Arwa VPS pattern |

### The no-Docker trade-off, named explicitly

Going Docker-less is consistent with the existing Arwa VPS setup and is
genuinely fine at MVP/early scale. At "hundreds+ statements/day,
multi-tenant, growth planned," the lack of containerization will eventually
show up in two places:

1. **Reproducing the exact dependency stack** (Tesseract version, OpenCV,
   Python packages) when adding a second server — a `requirements.txt` and
   a documented `apt install` list (see `docs/vps-setup.md`, to be written)
   substitute for this manually.
2. **Isolating one tenant's runaway OCR job** from starving others — Celery
   concurrency limits and per-tenant rate limiting are the mitigation until/
   unless containerization is revisited.

Neither is urgent today. Revisit if either becomes an actual incident, not
preemptively.

## Multi-tenancy

- **Isolation model**: shared database, shared schema, with a `tenant_id`
  column on every tenant-owned table (see `TenantScopedMixin` in
  `backend/app/db/base.py`) **enforced via PostgreSQL Row-Level Security**,
  not application-layer filtering alone. For a product handling bank
  statement data, a single missed `WHERE tenant_id = ...` in application
  code must not be able to leak one tenant's financial data to another —
  RLS is the backstop. The RLS policies themselves are TODO in the first
  real migration; the model layer is ready for them.
- Revisit dedicated databases per tenant only if/when a large regulated
  customer requires it — premature isolation costs real operational
  complexity for no benefit at current scale.
- **RBAC**: owner/admin/member roles per tenant (see `UserRole` in
  `backend/app/models/user.py`). Fine-grained per-resource permissions can
  wait until an enterprise customer asks.

## Compliance posture

Canadian company handling client financial data → **PIPEDA** is the
baseline (not GDPR/HIPAA/PCI — no EU/US health data, no card payment
processing in scope for the extraction product itself). Practical
requirements: encryption at rest and in transit, a documented data
retention policy, and a documented breach-notification process. SOC 2
becomes relevant once selling to accounting firms with their own
compliance obligations to their clients — worth planning for ahead of an
enterprise sales conversation, not urgent at MVP.

Per the original extraction skill's privacy principle, carried forward
here: never persist full card/account numbers beyond what's needed to
identify a statement.

## Extraction pipeline

1. **Ingest** (`services/extraction/ingestion.py`) — check for an
   extractable text layer to route text-PDF vs. scanned-PDF path. No ML.
2. **Text-based PDFs** (`services/extraction/text_pdf_extractor.py`) —
   pdfplumber/PyMuPDF line and table extraction. This is the accuracy
   floor and should handle most real statements, since most bank/card
   statements are generated as text PDFs, not scans.
3. **Scanned/image PDFs** (`services/extraction/ocr_extractor.py`) —
   OpenCV preprocessing (deskew, denoise, binarize) then Tesseract OCR
   with word-level bounding boxes and confidence scores.
4. **Institution/template matching** — MVP uses a deterministic keyword
   matcher (`services/extraction/template_matcher.py`, seeded with the 14
   institutions validated during the original skill's development: RBC,
   TD, Scotiabank, BMO, CIBC, National Bank, Desjardins, Tangerine,
   Simplii, EQ Bank, Wealthsimple, American Express, Rogers Bank, Triangle
   Mastercard). The classical ML classifier
   (`services/ml/template_classifier.py`) is a planned upgrade once enough
   labeled training data exists to outperform the keyword matcher — not
   before.
5. **Field extraction** — per-template deterministic rules for known
   institutions (highest confidence); a generic CRF-based field tagger is
   the planned fallback for unrecognized layouts (not yet implemented).
6. **Debit/credit classification** — rule-based per template first
   (mirroring the original skill's logic: use the statement's own column
   headers/section headers/keywords, never assume sign alone means debit).
   ML classifier as fallback for genuinely ambiguous single-amount-column
   statements (the Rogers Bank case from the original skill's testing).
7. **Confidence scoring** — every row gets a confidence score; anything
   below threshold is flagged `is_uncertain` and routed to human review.
8. **Human review** (`frontend/src/pages/ReviewPage.tsx`) — editable table,
   flagged rows highlighted. Every correction is persisted as an
   `MLTrainingSample`, which is the improvement loop that substitutes for
   calling an LLM API at inference time: periodically retrain the
   classical models on the growing corpus instead.

## Data model summary

`tenants`, `users` (role-based, tenant-scoped), `statements` (upload +
detected institution + status), `extraction_jobs` (Celery task tracking),
`transactions` (raw + parsed fields, confidence, review state),
`institution_templates` (versioned parsing rules — versioned because
institutions change statement layouts periodically, which silently breaks
a template), `ml_training_samples` (correction corpus for retraining).

## Roadmap

1. **MVP** (current) — text-based PDF path only, the ~14 already-validated
   institution templates, no ML classifier yet (keyword matcher only),
   mandatory review UI for every row. Runs locally, not yet deployed.
2. **Phase 2** — Tesseract OCR path fully wired end-to-end, expand template
   library, bring the classical ML template-classifier online once
   sufficient labeled data exists.
3. **Phase 3** — CRF fallback for unrecognized layouts, confidence
   scoring end-to-end, active-learning retraining loop, move to VPS,
   Stripe billing, harden multi-tenancy (RLS policies live).
4. **Phase 4** — optional external API integrations (explicitly deferred
   by the founder to "future extension," not MVP scope), SOC 2 groundwork
   if enterprise accounting-firm customers require it.

## Known risks (named explicitly, not buried)

- **Template drift**: institutions change statement layouts without
  notice, silently degrading a previously-accurate template. Needs
  monitoring (e.g., a spike in `is_uncertain` rate for a given institution)
  once in production — not built yet.
- **OCR accuracy ceiling**: scanned/photographed statements will always
  have a materially higher error rate than text PDFs; the review step is
  load-bearing here, not optional polish.
- **No-Docker operational risk at scale**: see the trade-off section above.
- **Financial PII handling**: statements are about as sensitive as data
  gets short of health records — encryption, retention limits, and RLS are
  not optional hardening to defer.
