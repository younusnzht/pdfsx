"""
Background task(s) that run the full extraction pipeline. Kept as a single
task per statement for MVP simplicity; split into a Celery chain
(ingest -> extract -> classify -> score) once individual steps need
independent retry/backoff behavior.
"""
from app.services.extraction.ingestion import detect_source_type
from app.services.extraction.template_matcher import match_institution
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="extract_statement")
def extract_statement_task(self, statement_id: str, pdf_path: str) -> dict:
    """
    Pipeline steps (fleshed out incrementally — this is the skeleton):
      1. detect_source_type -> text_pdf vs scanned_pdf
      2. text_pdf: pdfplumber/PyMuPDF line & table extraction
         scanned_pdf: OCR preprocessing + Tesseract
      3. match_institution (keyword matcher first; ML classifier once trained)
      4. apply institution_templates rules, or fall back to generic field
         tagging for unknown layouts
      5. classify debit/credit per-row
      6. score confidence per row, flag low-confidence rows
      7. persist Transaction rows, update Statement.status
    """
    source_type, page_count = detect_source_type(pdf_path)

    # TODO: branch on source_type, run the appropriate extractor,
    # persist rows to the transactions table, update ExtractionJob status.

    return {
        "statement_id": statement_id,
        "source_type": source_type.value,
        "page_count": page_count,
        "status": "skeleton_only_not_yet_implemented",
    }
