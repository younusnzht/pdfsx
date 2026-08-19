"""
Generic field extraction for statements without a specific institution
template yet. Works from pdfplumber's table extraction: finds a header
row by keyword, maps columns, then reads each row as a transaction.

Handles two different sign conventions depending on statement type,
since they're genuinely opposite:
  - Bank account (chequing/savings): "+" = deposit/credit, "-" = withdrawal/debit
  - Credit card: positive = purchase/debit, negative = payment-or-credit
statement_type is guessed from header text (see classify_statement_type)
when there's no separate Debit/Credit column to read directly — this
guess only matters for the single-Amount-column case; a statement with
real Debit/Credit or Withdrawal/Deposit columns is read directly from
those, no guessing involved.

Encodes several rules validated during the original skill's development:
carry a date down to rows that don't repeat it, exclude balance/subtotal
lines, and flag (rather than guess) genuinely ambiguous debit/credit
classification instead of assuming sign always means the same thing.
"""
import re
from dataclasses import dataclass

DATE_HEADERS = {"date", "transaction date", "trans date", "posting date", "post date"}
DESCRIPTION_HEADERS = {"description", "transaction description", "details", "merchant", "activity description"}
DEBIT_HEADERS = {"debit", "withdrawal", "withdrawals", "cheques & debits", "purchases"}
CREDIT_HEADERS = {"credit", "deposit", "deposits", "deposits & credits"}
AMOUNT_HEADERS = {"amount", "amount ($)", "amount($)"}
BALANCE_HEADERS = {"balance", "balance ($)", "balance($)"}

# Description-text signals that override the sign-based guess — these
# apply regardless of statement type, since "the description says it's a
# payment" is more reliable than any sign convention.
CREDIT_TEXT_SIGNALS = ("refund", "payment received", "reversal", "credit adjustment")
DEBIT_TEXT_SIGNALS = ("fee", "interest charge", "purchase")

EXCLUDED_DESCRIPTIONS = {"balance forward", "closing balance", "previous statement balance", "opening balance"}

CREDIT_CARD_SIGNALS = (
    "credit limit", "minimum payment", "statement balance", "annual percentage rate",
    "available credit", "cash advance", "apr", "credit card",
)
BANK_ACCOUNT_SIGNALS = (
    "chequing", "checking", "savings account", "opening balance", "account activity",
    "transit number", "routing number", "account statement",
)


@dataclass
class ExtractedRow:
    raw_date: str
    raw_description: str
    raw_debit: str | None
    raw_credit: str | None
    raw_balance: str | None
    confidence: float
    is_uncertain: bool
    raw_account: str | None = None


def classify_statement_type(header_text: str) -> str:
    """Returns 'credit_card' or 'bank_account' — only matters for the
    single-Amount-column sign convention below; defaults to bank_account
    when signals are unclear, since that's the more common statement type
    and its sign convention ("+" = credit) matches plain-English intuition,
    making a wrong default less silently confusing than the reverse."""
    lowered = header_text.lower()
    if any(signal in lowered for signal in CREDIT_CARD_SIGNALS):
        return "credit_card"
    if any(signal in lowered for signal in BANK_ACCOUNT_SIGNALS):
        return "bank_account"
    return "bank_account"


def _normalize(cell: str | None) -> str:
    return re.sub(r"\s+", " ", (cell or "")).strip().lower()


def _find_header_row(table: list[list[str | None]]) -> tuple[int, dict[str, int]] | None:
    for row_index, row in enumerate(table[:3]):
        normalized = [_normalize(cell) for cell in row]
        column_map: dict[str, int] = {}
        for col_index, cell in enumerate(normalized):
            if cell in DATE_HEADERS:
                column_map["date"] = col_index
            elif cell in DESCRIPTION_HEADERS:
                column_map["description"] = col_index
            elif cell in DEBIT_HEADERS:
                column_map["debit"] = col_index
            elif cell in CREDIT_HEADERS:
                column_map["credit"] = col_index
            elif cell in AMOUNT_HEADERS:
                column_map["amount"] = col_index
            elif cell in BALANCE_HEADERS:
                column_map["balance"] = col_index
        if "date" in column_map and "description" in column_map:
            return row_index, column_map
    return None


def _cell(row: list[str | None], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return (row[index] or "").strip()


def _classify_amount(amount_val: str, description: str, statement_type: str) -> tuple[str | None, str | None, float, bool]:
    """Returns (raw_debit, raw_credit, confidence, is_uncertain) for a
    single-Amount-column value."""
    lowered_description = description.lower()

    if any(signal in lowered_description for signal in CREDIT_TEXT_SIGNALS):
        return None, amount_val, 1.0, False
    if any(signal in lowered_description for signal in DEBIT_TEXT_SIGNALS):
        return amount_val, None, 1.0, False

    is_negative = amount_val.strip().startswith("-")
    is_positive_sign = amount_val.strip().startswith("+")

    if statement_type == "credit_card":
        # Positive/unsigned = purchase (debit); negative = payment/credit.
        if is_negative:
            return None, amount_val, 1.0, False
        return amount_val, None, 1.0, False

    # bank_account: "+" = deposit/credit, "-" = withdrawal/debit.
    if is_negative:
        return amount_val, None, 1.0, False
    if is_positive_sign:
        return None, amount_val, 1.0, False

    # No sign at all on a bank-account single-amount column — genuinely
    # ambiguous, flag rather than guess.
    return amount_val, None, 0.5, True


def extract_from_table(table: list[list[str | None]], statement_type: str = "bank_account") -> list[ExtractedRow]:
    header = _find_header_row(table)
    if header is None:
        return []
    header_row_index, column_map = header

    rows: list[ExtractedRow] = []
    last_date = ""

    for row in table[header_row_index + 1 :]:
        if row is None or all(cell is None or not str(cell).strip() for cell in row):
            continue

        date_cell = _cell(row, column_map.get("date"))
        description_cell = _cell(row, column_map.get("description"))
        if not description_cell:
            continue
        if description_cell.lower() in EXCLUDED_DESCRIPTIONS:
            continue

        raw_date = date_cell or last_date
        if date_cell:
            last_date = date_cell

        raw_balance = _cell(row, column_map.get("balance")) or None

        raw_debit: str | None = None
        raw_credit: str | None = None
        confidence = 1.0
        is_uncertain = False

        if "debit" in column_map and "credit" in column_map:
            raw_debit = _cell(row, column_map["debit"]) or None
            raw_credit = _cell(row, column_map["credit"]) or None
        elif "amount" in column_map:
            amount_val = _cell(row, column_map["amount"])
            if amount_val:
                raw_debit, raw_credit, confidence, is_uncertain = _classify_amount(
                    amount_val, description_cell, statement_type
                )

        rows.append(
            ExtractedRow(
                raw_date=raw_date,
                raw_description=description_cell,
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_balance=raw_balance,
                confidence=confidence,
                is_uncertain=is_uncertain,
            )
        )
    return rows


def extract_from_tables(tables: list[list[list[str | None]]], statement_type: str = "bank_account") -> list[ExtractedRow]:
    all_rows: list[ExtractedRow] = []
    for table in tables:
        all_rows.extend(extract_from_table(table, statement_type))
    return all_rows


# Line-based fallback for statements with no real table structure at all
# (no gridlines AND text-alignment table detection also fails, e.g. because
# it fragments words mid-token). Built against real Capital One statement
# text: "Mar 1 Deposit from Capital One Bank XXXXXX9057 Credit + $1,000.00
# $1,751.41" — date, description, an explicit Debit/Credit label, a sign,
# an amount, then a running balance. The explicit label is trusted as the
# primary source of truth (matches the skill's core principle); the sign is
# used only as a cross-check, flagging disagreement rather than guessing.
LINE_TRANSACTION_PATTERN = re.compile(
    r"^(?P<date>[A-Z][a-z]{2}\s+\d{1,2})\s+"
    r"(?P<description>.*?)"
    r"\s*(?P<category>Debit|Credit)\s+"
    r"(?P<sign>[+-])\s*"
    r"(?P<amount>\$[\d,]+\.\d{2})\s+"
    r"(?P<balance>\$[\d,]+\.\d{2})\s*$"
)


def extract_from_lines(lines: list) -> list[ExtractedRow]:
    rows: list[ExtractedRow] = []
    for line in lines:
        text = line.text.strip()
        match = LINE_TRANSACTION_PATTERN.match(text)
        if not match:
            continue  # not a transaction line — balance summaries, rejected-transaction notices, page headers, etc. all correctly fall through here since they don't carry an explicit Debit/Credit label

        date = match.group("date")
        description = match.group("description").strip()  # can legitimately be empty — some real rows have no merchant text at all; that's preserved faithfully, not invented
        category = match.group("category").lower()
        sign = match.group("sign")
        amount = match.group("amount")
        balance = match.group("balance")

        raw_debit = amount if category == "debit" else None
        raw_credit = amount if category == "credit" else None

        expected_sign = "-" if category == "debit" else "+"
        confidence = 1.0
        is_uncertain = False
        if sign != expected_sign:
            confidence = 0.5
            is_uncertain = True

        rows.append(
            ExtractedRow(
                raw_date=date,
                raw_description=description,
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_balance=balance,
                confidence=confidence,
                is_uncertain=is_uncertain,
            )
        )
    return rows


# --- Multi-account section detection ---
#
# Some statements (e.g. Capital One's combined checking/savings summary)
# bundle several sub-accounts into one PDF, each with its own full
# transaction history for the period. Without tracking which account each
# row belongs to, a bookkeeping tool can't tell "$1.96 interest" apart
# across four different accounts — a real correctness gap, not cosmetic.
#
# The trick: page 1 always prints a summary line pairing each account name
# with its opening and closing balance for the period, e.g.
#   "Genreal Spendings $751.41 $2,701.12"
# and each account's own transaction section later in the document starts
# with a line repeating that exact opening balance, e.g.
#   "Mar 1 Opening Balance $751.41"
# Matching on that shared dollar amount reliably ties each section back to
# its real account name — no guessing, no hardcoded account list.

ACCOUNT_SUMMARY_PATTERN = re.compile(
    r"^(?P<account>[A-Za-z][A-Za-z ]{2,40}?)\s+\$(?P<opening>[\d,]+\.\d{2})\s+\$(?P<closing>[\d,]+\.\d{2})\s*$"
)
OPENING_BALANCE_PATTERN = re.compile(
    r"^[A-Z][a-z]{2}\s+\d{1,2}\s+Opening Balance\s+\$(?P<amount>[\d,]+\.\d{2})\s*$"
)


def _build_opening_balance_to_account_map(lines: list) -> dict[str, str]:
    balance_to_account: dict[str, str] = {}
    for line in lines:
        match = ACCOUNT_SUMMARY_PATTERN.match(line.text.strip())
        if match:
            balance_to_account[match.group("opening")] = match.group("account").strip()
    return balance_to_account


def extract_from_lines_with_accounts(lines: list) -> list[ExtractedRow]:
    """Same as extract_from_lines, but tags each row with the account it
    belongs to when the statement contains a page-1 account summary table.
    Falls back to raw_account=None for every row if no such summary is
    found (i.e. this is a single-account statement, or an account summary
    in a format this pattern doesn't recognize yet) — never invents an
    account name it can't actually verify against the source."""
    balance_to_account = _build_opening_balance_to_account_map(lines)

    rows: list[ExtractedRow] = []
    current_account: str | None = None

    for line in lines:
        text = line.text.strip()

        opening_match = OPENING_BALANCE_PATTERN.match(text)
        if opening_match:
            current_account = balance_to_account.get(opening_match.group("amount"))
            continue

        match = LINE_TRANSACTION_PATTERN.match(text)
        if not match:
            continue

        date = match.group("date")
        description = match.group("description").strip()
        category = match.group("category").lower()
        sign = match.group("sign")
        amount = match.group("amount")
        balance = match.group("balance")

        raw_debit = amount if category == "debit" else None
        raw_credit = amount if category == "credit" else None

        expected_sign = "-" if category == "debit" else "+"
        confidence = 1.0
        is_uncertain = False
        if sign != expected_sign:
            confidence = 0.5
            is_uncertain = True

        rows.append(
            ExtractedRow(
                raw_date=date,
                raw_description=description,
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_balance=balance,
                confidence=confidence,
                is_uncertain=is_uncertain,
                raw_account=current_account,
            )
        )
    return rows


# --- Two-date credit-card format (RBC, Amex, Rogers, Triangle, and most
# Canadian credit card statements) ---
#
# Unlike Capital One's bank-account lines (one date, an explicit
# Debit/Credit word), credit card statements typically show Transaction
# Date + Posting Date + Description + a single Amount with no explicit
# label at all — e.g. "DEC 29 JAN 02 MOBILE SENTRIX CANADA CONCORD ON
# $467.30" (RBC) or "Mar14 Mar16 00201 MACS CONV. STORES VANIER 16.98"
# (Amex — note no space before the day, and no $ sign at all).
#
# Sign alone isn't reliable here: some issuers show a purchase as a bare
# positive number and a payment as "-$X" (RBC, TD, Rogers), but others
# (confirmed on a real Amex Business Platinum statement) show every line
# — purchases included — with a leading minus regardless of type. Section
# headers ("New Payments" vs "New Transactions", "Payments received" vs
# "Purchases") are the reliable signal, exactly as the original skill's
# testing found. Sign is used only as a fallback when no section header
# has been seen yet.

TWO_DATE_LINE_PATTERN = re.compile(
    r"^(?P<date>[A-Za-z]{3}\.?\s?\d{1,2}(?:,?\s*\d{4})?)\s+"
    r"(?P<posting>[A-Za-z]{3}\.?\s?\d{1,2}(?:,?\s*\d{4})?)\s+"
    r"(?P<description>.*?)\s+"
    r"(?P<sign>-)?\$?(?P<amount>[\d,]+\.\d{2})\s*$"
)

PAYMENT_SECTION_HEADERS = ("new payments", "payments received", "your payments", "total payments")
CREDIT_SECTION_HEADERS = ("returns and other credits", "return and other credits", "your interest")
PURCHASE_SECTION_HEADERS = ("new transactions", "purchases", "your new charges", "total purchases")


def _classify_two_date_line(description: str, sign: str | None, section: str | None) -> tuple[bool, float, bool]:
    """Returns (is_credit, confidence, is_uncertain). Sign is trusted at
    full confidence by default — it was correct across every real
    statement tested (RBC, TD, Rogers, Triangle) that doesn't use section
    headers at all. The section-header override exists specifically for
    statements where sign is known to be unreliable (the Amex Business
    Platinum case, where every line — purchases included — prints a
    leading minus); it doesn't mean sign alone is untrustworthy elsewhere."""
    if section == "payment":
        return True, 1.0, False
    if section == "purchase":
        return False, 1.0, False
    return (sign == "-"), 1.0, False


def extract_from_lines_two_date_format(lines: list) -> list[ExtractedRow]:
    rows: list[ExtractedRow] = []
    current_section: str | None = None

    for line in lines:
        text = line.text.strip()
        lowered = text.lower()

        if any(h in lowered for h in PAYMENT_SECTION_HEADERS):
            current_section = "payment"
        elif any(h in lowered for h in CREDIT_SECTION_HEADERS):
            current_section = "payment"
        elif any(h in lowered for h in PURCHASE_SECTION_HEADERS):
            current_section = "purchase"

        match = TWO_DATE_LINE_PATTERN.match(text)
        if not match:
            continue

        date = match.group("date")
        description = match.group("description").strip()
        sign = match.group("sign")
        amount = match.group("amount")

        if not description or description.lower() in EXCLUDED_DESCRIPTIONS:
            continue

        is_credit, confidence, is_uncertain = _classify_two_date_line(description, sign, current_section)

        rows.append(
            ExtractedRow(
                raw_date=date,
                raw_description=description,
                raw_debit=None if is_credit else amount,
                raw_credit=amount if is_credit else None,
                raw_balance=None,
                confidence=confidence,
                is_uncertain=is_uncertain,
            )
        )
    return rows


# --- Positional multi-line bank account table (Alterna, BMO, CIBC, RBC,
# Scotiabank business/personal account statements, and likely most other
# Canadian bank account statements) ---
#
# These statements share a shape: Date | Description (often spanning
# multiple lines) | a Withdrawal/Debit column | a Deposit/Credit column |
# a running Balance column — but flattened to plain text, a row like
# "25 Apr. Credit Funding Member shares 15.00 15.00" gives no label and no
# sign to say whether 15.00 is a withdrawal or a deposit. The only signal
# left is which column x-range the number originally sat under, so this
# extractor works from individual word positions (extract_words) rather
# than flattened line text, and locates the Debit/Credit column boundaries
# from the header row itself before classifying any amount.

AMOUNT_TOKEN_PATTERN = re.compile(r"^\$?-?(?:\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+\.\d{1,2})$")
MONTH_NAMES = {"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"}


def _is_month_token(text: str) -> bool:
    return text.strip(".").lower() in MONTH_NAMES


def _is_day_token(text: str) -> bool:
    t = text.strip(".,")
    return t.isdigit() and 1 <= int(t) <= 31


def _consume_date_prefix(tokens: list) -> int:
    """Returns how many leading tokens form a date, or 0. Deliberately
    strict — only real month names and numeric day tokens count, never
    arbitrary words — after an earlier looser pattern was found to match
    ordinary description words like "AMERICAN" or "POINT" as if they were
    dates, silently scrambling every row on statements that don't repeat
    the date on every line (CIBC, Scotiabank)."""
    if len(tokens) >= 2:
        t0, t1 = tokens[0].text, tokens[1].text
        if _is_month_token(t0) and _is_day_token(t1):
            return 2  # "Sep 19"
        if _is_day_token(t0) and _is_month_token(t1):
            return 2  # "01 Apr."
    if len(tokens) >= 1 and re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", tokens[0].text):
        return 1  # "05/01/2025"
    return 0


DEBIT_COLUMN_WORDS = {"withdrawal", "withdrawals", "debit", "debits", "cheques", "cheque"}
CREDIT_COLUMN_WORDS = {"deposit", "deposits", "credit", "credits"}
BALANCE_COLUMN_WORDS = {"balance"}

ROW_EXCLUDED_DESCRIPTIONS = {
    "balance forward", "opening balance", "closing balance", "closing totals",
    "previous balance", "total", "totals",
}


def _find_column_header(rows: list[list]) -> tuple[int, float | None, float | None, float | None] | None:
    """Scans for the header row and returns (row_index, debit_x, credit_x,
    balance_x). Checks a 2-row window (not just one row) before accepting a
    match, since some statements (BMO) split the header across two physical
    lines — "Amounts debited / Amounts credited" on one line, "Date
    Description ... Balance" on the next. Still requires a "date"-ish word
    somewhere in that window, since without it a plain "Withdrawals" /
    "debited" mention in an account-summary box above the real table (BMO,
    CIBC both do this) would otherwise be mistaken for the header."""
    for i, row in enumerate(rows):
        window = row + (rows[i + 1] if i + 1 < len(rows) else [])
        words_lower = [w.text.strip("()$: ").lower() for w in window]
        if not any(w.startswith("date") for w in words_lower):
            continue
        debit_x = credit_x = balance_x = None
        for word, lowered in zip(window, words_lower):
            if debit_x is None and any(lowered.startswith(w) for w in DEBIT_COLUMN_WORDS):
                debit_x = word.x0
            elif credit_x is None and any(lowered.startswith(w) for w in CREDIT_COLUMN_WORDS):
                credit_x = word.x0
            elif balance_x is None and lowered.startswith("balance"):
                balance_x = word.x0
        if debit_x is not None or credit_x is not None:
            return i, debit_x, credit_x, balance_x
    return None


def extract_from_positional_table(word_rows: list[list]) -> list[ExtractedRow]:
    """
    State machine note: a transaction's amount appears on the SAME row as
    its first description line (not after all description lines) — e.g.
    CIBC prints "Sep 17 INTERNET BILL PMT000000110812  1,000.00  38,888.13"
    and only THEN follows with extra description detail on subsequent
    text-only lines ("AMERICAN EXPRESS CARDS", "4506*********950") that
    belong to that SAME transaction, not the next one. So a transaction is
    finalized when the NEXT amount-bearing row is reached (or the table
    ends), not immediately upon seeing its own amount — text-only rows in
    between always extend the currently-open transaction.
    """
    header = _find_column_header(word_rows)
    if header is None:
        return []
    header_index, debit_x, credit_x, balance_x = header

    def classify(x0: float) -> str:
        """Classifies a single amount by nearest known column. Falls back
        sensibly when balance_x wasn't found (most statements) — compares
        only debit vs. credit in that case, same as before."""
        candidates = {}
        if debit_x is not None:
            candidates["debit"] = abs(x0 - debit_x)
        if credit_x is not None:
            candidates["credit"] = abs(x0 - credit_x)
        if balance_x is not None:
            candidates["balance"] = abs(x0 - balance_x)
        if not candidates:
            return "credit"
        return min(candidates, key=candidates.get)

    results: list[ExtractedRow] = []
    last_date = ""
    pending: dict | None = None  # currently-open transaction, extended by continuation rows
    orphan_text_parts: list[str] = []  # text lines seen while no transaction is open yet — attach to the next one that opens, rather than silently dropping them (e.g. a description line arriving right after the prior transaction finalized but before this one's amount row)

    def finalize(p: dict) -> ExtractedRow | None:
        description = " ".join(p["description_parts"]).strip()
        if not description or description.lower() in ROW_EXCLUDED_DESCRIPTIONS:
            return None
        return ExtractedRow(
            raw_date=p["date"],
            raw_description=description,
            raw_debit=p["debit"],
            raw_credit=p["credit"],
            raw_balance=p["balance"],
            confidence=p["confidence"],
            is_uncertain=p["is_uncertain"],
        )

    for row in word_rows[header_index + 1 :]:
        if not row:
            continue

        amount_words = [w for w in row if AMOUNT_TOKEN_PATTERN.match(w.text)]
        text_words = [w for w in row if w not in amount_words]

        consumed = _consume_date_prefix(text_words)
        row_date = " ".join(w.text for w in text_words[:consumed]) if consumed else ""
        remaining_text_words = text_words[consumed:]
        row_description = " ".join(w.text for w in remaining_text_words).strip()

        if row_description.lower().startswith(("no. of debit", "no. of credit", "please examine",
                                                 "this is your official", "uncollected fees")):
            break

        if not amount_words:
            # Pure continuation line — extends the currently-open transaction.
            if pending is not None and row_description:
                pending["description_parts"].append(row_description)
            continue

        # This row starts a new transaction — finalize whatever was open,
        # regardless of what this row turns out to be (even a pure
        # balance-marker row like "Balance forward $0.00" must still
        # finalize the prior transaction first, not silently discard it).
        if pending is not None:
            finalized = finalize(pending)
            if finalized is not None:
                results.append(finalized)
            pending = None

        raw_date = row_date or last_date
        if row_date:
            last_date = row_date

        # Balance-marker rows ("Opening balance", "Closing totals", etc.)
        # must never become an open transaction themselves — if they did,
        # any header/section text appearing before the *next* real amount
        # row would wrongly accumulate into their description instead of
        # being discarded (this is exactly what happened on Alterna's
        # second sub-account table before this check was added).
        if row_description.lower() in ROW_EXCLUDED_DESCRIPTIONS:
            continue

        if not amount_words:
            continue

        raw_debit = raw_credit = raw_balance = None
        confidence = 1.0
        is_uncertain = False

        # Classify every amount token independently by nearest column,
        # rather than assuming the last one is always the balance — RBC's
        # deposit rows often show only a transaction amount with no
        # balance on that line at all (balance only updates on some rows),
        # so a fixed "last = balance" assumption silently discarded real
        # deposits before this per-token classification was added.
        for amt in amount_words:
            side = classify(amt.x0)
            if side == "debit" and raw_debit is None:
                raw_debit = amt.text
            elif side == "credit" and raw_credit is None:
                raw_credit = amt.text
            elif side == "balance" and raw_balance is None:
                raw_balance = amt.text
            else:
                confidence = 0.5
                is_uncertain = True

        if raw_debit is None and raw_credit is None:
            # Nothing classified as an actual transaction amount — this is
            # a pure balance-marker row (e.g. "Balance forward $0.00").
            # Prior pending was already finalized above; nothing to open.
            continue

        if debit_x is None or credit_x is None:
            confidence = min(confidence, 0.6)
            is_uncertain = True

        pending = {
            "date": raw_date,
            "description_parts": [row_description] if row_description else [],
            "debit": raw_debit,
            "credit": raw_credit,
            "balance": raw_balance,
            "confidence": confidence,
            "is_uncertain": is_uncertain,
        }

    if pending is not None:
        finalized = finalize(pending)
        if finalized is not None:
            results.append(finalized)

    return results
