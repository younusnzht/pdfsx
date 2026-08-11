"""
Deterministic extraction for PDFs with a real text layer — no OCR, no ML.
This is the highest-accuracy path and should handle the majority of real
bank/card statements, since most are generated as text PDFs, not scans.

Returns raw positioned text lines; institution-specific template rules
(see services/extraction/template_matcher.py and field_extractor.py) turn
this into actual transaction rows.
"""
from dataclasses import dataclass

import pdfplumber


@dataclass
class TextLine:
    page_number: int
    text: str
    x0: float
    top: float


def extract_lines(pdf_path: str) -> list[TextLine]:
    lines: list[TextLine] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for line in page.extract_text_lines():
                lines.append(
                    TextLine(
                        page_number=page_number,
                        text=line["text"],
                        x0=line["x0"],
                        top=line["top"],
                    )
                )
    return lines


def extract_tables(pdf_path: str) -> list[list[list[str]]]:
    """Table-shaped extraction for statements with clean gridlines/columns —
    often cleaner than line-based extraction for column-aligned statements."""
    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                all_tables.append(table)
    return all_tables
