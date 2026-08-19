"""
Deterministic extraction for PDFs with a real text layer — no OCR, no ML.
This is the highest-accuracy path and should handle the majority of real
bank/card statements, since most are generated as text PDFs, not scans.

Returns raw positioned text lines; institution-specific template rules
(see services/extraction/template_matcher.py and field_extractor.py) turn
this into actual transaction rows.
"""
from collections import defaultdict
from dataclasses import dataclass

import fitz  # PyMuPDF
import pdfplumber


@dataclass
class TextLine:
    page_number: int
    text: str
    x0: float
    top: float


@dataclass
class Word:
    page_number: int
    top: float
    x0: float
    text: str


def _cluster_words_by_row(page, page_number: int) -> dict[int, list[tuple[float, str]]]:
    words = page.get_text("words")  # (x0, y0, x1, y1, text, block, line, word_no)
    by_y: dict[int, list[tuple[float, str]]] = defaultdict(list)
    for x0, y0, x1, y1, text, *_ in words:
        by_y[round(y0)].append((x0, text))
    return by_y


def extract_lines(pdf_path: str) -> list[TextLine]:
    """
    Reconstructs visual lines by clustering PyMuPDF's word-level output by
    y-position, rather than trusting either library's built-in line/text
    joining. This matters because both pdfplumber's extract_text_lines()
    and naive PyMuPDF text extraction were found (against real statements —
    RBC, TD, Rogers Bank, Triangle Mastercard) to sometimes drop the space
    between words entirely ("TIMHORTONS#2399OTTAWA"), which silently breaks
    both institution-keyword matching and any line-based regex parsing.
    Reconstructing from individual word bounding boxes and joining with an
    explicit space avoids that failure mode.
    """
    lines: list[TextLine] = []
    doc = fitz.open(pdf_path)
    for page_number, page in enumerate(doc, start=1):
        by_y = _cluster_words_by_row(page, page_number)
        for y in sorted(by_y.keys()):
            parts = sorted(by_y[y], key=lambda p: p[0])
            line_text = " ".join(t for _, t in parts)
            x0 = parts[0][0] if parts else 0.0
            lines.append(TextLine(page_number=page_number, text=line_text, x0=x0, top=float(y)))
    doc.close()
    return lines


def extract_words(pdf_path: str) -> list[list[Word]]:
    """
    Returns words grouped by visual row (same y-clustering as extract_lines,
    but keeping each word's individual x0 instead of flattening to a single
    string). Needed for statements where a bare number's meaning — debit vs.
    credit — can only be recovered from which column x-range it falls under,
    since the source statement has no explicit label or sign on the amount
    itself (common on bank account statements: Alterna, BMO, CIBC, RBC,
    Scotiabank business accounts all use this Date/Description/Withdrawal-
    column/Deposit-column/Balance-column shape with nothing on the line
    itself to say which column a given number came from).
    """
    rows: list[list[Word]] = []
    doc = fitz.open(pdf_path)
    for page_number, page in enumerate(doc, start=1):
        by_y = _cluster_words_by_row(page, page_number)
        for y in sorted(by_y.keys()):
            parts = sorted(by_y[y], key=lambda p: p[0])
            rows.append([Word(page_number=page_number, top=float(y), x0=x0, text=t) for x0, t in parts])
    doc.close()
    return rows


def extract_tables(pdf_path: str) -> list[list[list[str]]]:
    """Table-shaped extraction for statements with clean gridlines/columns —
    often cleaner than line-based extraction for column-aligned statements."""
    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                all_tables.append(table)
    return all_tables


def extract_tables_by_text_alignment(pdf_path: str) -> list[list[list[str]]]:
    """Fallback for statements with no drawn gridlines (common — many banks
    render statements as plain aligned text, not an actual table object in
    the PDF). Instead of looking for drawn lines, this clusters words into
    rows/columns purely by their x/y text alignment, which handles
    "borderless" layouts far better than the default lattice detection in
    extract_tables() above. Try this when extract_tables() returns nothing
    useful (empty tables, or tables fragmented into single-column pieces
    with no date/description attached)."""
    settings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "intersection_tolerance": 5,
    }
    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables(table_settings=settings):
                all_tables.append(table)
    return all_tables
