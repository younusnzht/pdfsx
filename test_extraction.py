"""
Standalone extraction test — runs the pipeline against a real PDF without
touching the database or Celery, so extraction accuracy can be tuned
quickly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz  # noqa: E402

from app.services.extraction.field_extractor import (  # noqa: E402
    classify_statement_type,
    extract_from_lines_two_date_format,
    extract_from_lines_with_accounts,
    extract_from_tables,
)
from app.services.extraction.ingestion import detect_source_type  # noqa: E402
from app.services.extraction.template_matcher import match_institution  # noqa: E402
from app.services.extraction.text_pdf_extractor import (  # noqa: E402
    extract_lines,
    extract_tables,
    extract_tables_by_text_alignment,
)


def print_rows(rows):
    print(f"\nExtracted {len(rows)} transaction rows:\n")
    print(f"{'Account':<18} {'Date':<10} {'Description':<40} {'Debit':>10} {'Credit':>10}  Conf")
    print("-" * 108)
    for row in rows:
        flag = "  [UNCERTAIN]" if row.is_uncertain else ""
        account = (getattr(row, "raw_account", None) or "")[:18]
        description = row.raw_description[:40]
        print(
            f"{account:<18} {row.raw_date:<10} {description:<40} "
            f"{(row.raw_debit or ''):>10} {(row.raw_credit or ''):>10}  {row.confidence:.2f}{flag}"
        )


def main(pdf_path: str) -> None:
    source_type, page_count = detect_source_type(pdf_path)
    print(f"Source type: {source_type.value} | Pages: {page_count}")

    doc = fitz.open(pdf_path)
    header_text = doc[0].get_text("text")[:800]
    doc.close()

    match = match_institution(header_text)
    print(f"Institution match: {match.institution or 'unknown (not in the seeded keyword list)'}")

    statement_type = classify_statement_type(header_text)
    print(f"Statement type guess: {statement_type}")

    if source_type.value != "text_pdf":
        print("\nThis is a scanned/image PDF — the OCR path isn't wired into this test script yet.")
        return

    tables = extract_tables(pdf_path)
    rows = extract_from_tables(tables, statement_type) if tables else []
    if rows:
        print(f"\n[Lattice table strategy worked — {len(tables)} tables]")
        print_rows(rows)
        return

    tables2 = extract_tables_by_text_alignment(pdf_path)
    rows2 = extract_from_tables(tables2, statement_type) if tables2 else []
    if rows2:
        print(f"\n[Text-alignment table strategy worked — {len(tables2)} tables]")
        print_rows(rows2)
        return

    print("\nNo usable table structure found — falling back to line-based extraction.")
    lines = extract_lines(pdf_path)

    rows3 = extract_from_lines_with_accounts(lines)
    if rows3:
        accounts_found = sorted({r.raw_account for r in rows3 if r.raw_account})
        print(f"\n[Single-date + label strategy worked — {len(rows3)} rows]")
        if accounts_found:
            print(f"Accounts detected: {accounts_found}")
        print_rows(rows3)
        return

    rows4 = extract_from_lines_two_date_format(lines)
    if rows4:
        print(f"\n[Two-date credit-card strategy worked — {len(rows4)} rows]")
        print_rows(rows4)
        return

    from app.services.extraction.field_extractor import extract_from_positional_table
    from app.services.extraction.text_pdf_extractor import extract_words

    word_rows = extract_words(pdf_path)
    rows5 = extract_from_positional_table(word_rows)
    if rows5:
        print(f"\n[Positional multi-line table strategy worked — {len(rows5)} rows]")
        print_rows(rows5)
        return

    print("\nNo transaction lines matched either. Printing raw lines for further diagnosis:\n")
    for ln in lines[:40]:
        print(f"p{ln.page_number} x0={ln.x0:.0f} top={ln.top:.0f} | {ln.text!r}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Usage: python scripts/test_extraction.py "path\\to\\statement.pdf"')
        sys.exit(1)
    main(sys.argv[1])
