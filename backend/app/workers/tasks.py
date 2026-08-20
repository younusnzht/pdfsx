"""
Background task(s) that run the full extraction pipeline. Kept as a single
task per statement for MVP simplicity; split into a Celery chain
(ingest -> extract -> classify -> score) once individual steps need
independent retry/backoff behavior.

Runs the same multi-strategy fallback chain validated by
scripts/test_extraction.py against 14 real Canadian statements:
  text_pdf:  lattice table -> text-alignment table -> single-date+label
             lines -> two-date credit-card lines -> positional multi-line
             table
  scanned_pdf / garbled text-extraction: OCR (Tesseract) -> positional
             multi-line table, using Tesseract's own line grouping

Celery tasks don't get FastAPI's request-scoped DB session via Depends —
each task opens and closes its own session directly from SessionLocal.
"""
import uuid

from app.db.session import SessionLocal
from app.models.extraction_job import ExtractionJob, JobStatus
from app.models.ml_training_sample import MLTrainingSample  # noqa: F401 (imported for Alembic metadata completeness)
from app.models.statement import Statement, StatementStatus
from app.models.transaction import Transaction
from app.services.extraction.field_extractor import (
    ExtractedRow,
    classify_statement_type,
    extract_from_lines_two_date_format,
    extract_from_lines_with_accounts,
    extract_from_positional_table,
    extract_from_tables,
)
from app.services.extraction.ingestion import detect_source_type
from app.services.extraction.template_matcher import match_institution
from app.services.extraction.text_pdf_extractor import (
    extract_lines,
    extract_tables,
    extract_tables_by_text_alignment,
    extract_words,
)
from app.workers.celery_app import celery_app


def _run_text_pdf_pipeline(pdf_path: str, statement_type: str) -> tuple[list[ExtractedRow], str]:
    """Returns (rows, strategy_name). Tries each strategy in order, same as
    the validated test script, stopping at the first one that finds rows."""
    tables = extract_tables(pdf_path)
    rows = extract_from_tables(tables, statement_type) if tables else []
    if rows:
        return rows, "lattice_table"

    tables2 = extract_tables_by_text_alignment(pdf_path)
    rows2 = extract_from_tables(tables2, statement_type) if tables2 else []
    if rows2:
        return rows2, "text_alignment_table"

    lines = extract_lines(pdf_path)

    rows3 = extract_from_lines_with_accounts(lines)
    if rows3:
        return rows3, "single_date_label"

    rows4 = extract_from_lines_two_date_format(lines)
    if rows4:
        return rows4, "two_date_credit_card"

    word_rows = extract_words(pdf_path)
    rows5 = extract_from_positional_table(word_rows)
    if rows5:
        return rows5, "positional_table"

    return [], "none"


def _run_ocr_pipeline(pdf_path: str) -> tuple[list[ExtractedRow], str]:
    from app.services.extraction.ocr_extractor import extract_word_rows_from_pdf

    word_rows = extract_word_rows_from_pdf(pdf_path)
    rows = extract_from_positional_table(word_rows)
    return (rows, "ocr_positional_table") if rows else ([], "none")


@celery_app.task(bind=True, name="extract_statement")
def extract_statement_task(self, statement_id: str, pdf_path: str) -> dict:
    db = SessionLocal()
    try:
        statement = db.get(Statement, uuid.UUID(statement_id))
        if statement is None:
            return {"statement_id": statement_id, "status": "statement_not_found"}

        job = ExtractionJob(
            tenant_id=statement.tenant_id,
            statement_id=statement.id,
            celery_task_id=self.request.id,
            status=JobStatus.running,
            current_step="detect_source_type",
        )
        db.add(job)
        statement.status = StatementStatus.processing
        db.commit()

        source_type, page_count = detect_source_type(pdf_path)
        statement.source_type = source_type
        statement.page_count = page_count

        try:
            import fitz

            doc = fitz.open(pdf_path)
            header_text = doc[0].get_text("text")[:800]
            doc.close()
        except Exception:
            header_text = ""

        match = match_institution(header_text)
        statement.institution = match.institution
        statement.institution_confidence = match.confidence
        statement_type = classify_statement_type(header_text)

        job.current_step = "extract"
        db.commit()

        if source_type.value == "text_pdf":
            rows, strategy = _run_text_pdf_pipeline(pdf_path, statement_type)
            if not rows:
                # Text extraction found no usable structure — this can
                # legitimately mean the PDF's embedded text is unreliable
                # (e.g. the scrambled-font case found on one real RBC
                # statement tonight), so fall back to OCR rather than
                # give up outright.
                rows, strategy = _run_ocr_pipeline(pdf_path)
        else:
            rows, strategy = _run_ocr_pipeline(pdf_path)

        job.current_step = "persist"
        db.commit()

        for order, row in enumerate(rows):
            db.add(
                Transaction(
                    tenant_id=statement.tenant_id,
                    statement_id=statement.id,
                    raw_date=row.raw_date,
                    raw_description=row.raw_description,
                    raw_debit=row.raw_debit,
                    raw_credit=row.raw_credit,
                    confidence=row.confidence,
                    is_uncertain=row.is_uncertain,
                    row_order=order,
                )
            )

        statement.status = StatementStatus.needs_review if rows else StatementStatus.failed
        if not rows:
            statement.error_message = (
                "No transactions could be extracted from this statement. "
                "It may use a layout not yet supported."
            )

        job.status = JobStatus.succeeded
        db.commit()

        return {
            "statement_id": statement_id,
            "source_type": source_type.value,
            "page_count": page_count,
            "institution": match.institution,
            "strategy": strategy,
            "rows_extracted": len(rows),
            "status": "succeeded" if rows else "no_rows_extracted",
        }
    except Exception as exc:
        db.rollback()
        statement = db.get(Statement, uuid.UUID(statement_id))
        if statement is not None:
            statement.status = StatementStatus.failed
            statement.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()
