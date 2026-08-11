"""
Step 1 of the pipeline: figure out whether a PDF has an extractable text
layer (fast, near-100%-accurate deterministic path) or is scanned/image-only
(needs the OCR path). No ML, no API calls — just checking text density.
"""
import fitz  # PyMuPDF

from app.models.statement import SourceType

MIN_CHARS_PER_PAGE_FOR_TEXT_PDF = 20


def detect_source_type(pdf_path: str) -> tuple[SourceType, int]:
    """Returns (source_type, page_count)."""
    doc = fitz.open(pdf_path)
    page_count = doc.page_count

    total_chars = 0
    for page in doc:
        total_chars += len(page.get_text("text").strip())

    avg_chars_per_page = total_chars / max(page_count, 1)
    doc.close()

    if avg_chars_per_page >= MIN_CHARS_PER_PAGE_FOR_TEXT_PDF:
        return SourceType.text_pdf, page_count
    return SourceType.scanned_pdf, page_count
