#!/usr/bin/env python3
"""Deterministic PBS row label-quality classifier (Task 5 of the
semantic-defect milestone).

Classifies a raw extracted PBS row label into exactly one of: program,
outcome, component, financial_statement_line, table_header, year_header,
unit_header, subtotal, total, narrative_fragment, malformed_concatenated_row,
unknown. Only program/outcome/component are `publishable` - eligible to
participate in the PBS -> Statement 6 crosswalk.

Deliberately does not rely on one regex. Each check below is an independent
structural signal - embedded numeric-value-token count, year-token count,
unit-token presence, a curated accounting-heading vocabulary, a curated
financial-statement line-item vocabulary, legislative-citation shape,
narrative-continuation shape, label length, and known program/outcome/
component numbering patterns - evaluated in a fixed precedence order from
"most certain this is broken" to "most certain this is a real program".
Anything that does not clearly satisfy a rejection rule AND does not clearly
look like a real program/outcome/component name is `unknown`, not
`program` - per the mission, absence of evidence is not evidence of
validity, and a clean-but-unlabelled row is excluded from the crosswalk
rather than guessed into it.

Extraction context: source_documents rows for federal_pbs_programs_all store
node.name as "{portfolio} / {program_label}" (see
scripts/ingest/extractors/pbs_programs_all.py, _append_year_rows'
`category` field) - portfolio is split off before classification so
classification signals only ever look at the row's own label text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Financial-year token: "2027-28", "2027–28", "2027‑28", "2027\xad28"
# (various dash glyphs seen from PDF text extraction - hyphen, en dash,
# non-breaking hyphen, and U+00AD soft hyphen, the one actually produced by
# the PBS PDF extractor, confirmed against data/facts.db), or "2027/28".
YEAR_TOKEN = re.compile(r"\b(?:19|20)\d{2}[\-‐‑‒–—\xad/](?:\d{2})\b")

# A real dollar-value token: has a thousands separator, or is parenthesized
# (accounting negative), or is a bare decimal - deliberately excludes bare
# small integers like "1" or "2024" which are far more likely to be part of
# a program/outcome number or a citation year than a financial value.
VALUE_TOKEN = re.compile(
    r"-?\(?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?|\(\d+(?:\.\d+)?\)"
)

UNIT_TOKEN = re.compile(r"\$'?\s?000\b|\$m\b|\$b\b|\('000\)|\(\$'000\)|^000$", re.I)

# Three or more consecutive bare (no thousands-separator) small numbers -
# e.g. "150 150 100" - a flattened row of $'000-denominated values too
# small to trip VALUE_TOKEN's thousands-separator requirement. Excludes a
# lone dotted program number like "1.1" by requiring at least three tokens
# in an unbroken run.
BARE_NUMERIC_RUN = re.compile(r"(?<![\d.])-?\d{1,4}(?:\s+-?\d{1,4}){2,}(?![\d.])")

# Whole-table-section headings only - "Employee benefits", "Suppliers" etc.
# are real line items *within* an EXPENSES section, not headings themselves,
# and are matched separately via FINANCIAL_STATEMENT_LINE_ITEMS below so a
# bare "Employee benefits" row classifies as financial_statement_line, not
# table_header.
ACCOUNTING_HEADINGS = re.compile(
    r"\b(EXPENSES|ASSETS|LIABILITIES|REVENUE|EQUITY|CASH FLOW|"
    r"OPERATING ACTIVITIES|INVESTING ACTIVITIES|"
    r"FINANCING ACTIVITIES|ADMINISTERED ON BEHALF OF GOVERNMENT|"
    r"COMPREHENSIVE INCOME|OWN-SOURCE INCOME|NON-TAXATION REVENUE)\b",
    re.I,
)

# Common AAS/GFS financial-statement line items that repeatedly show up as
# their own extracted "row" in PBS Section 3 tables - real accounting
# vocabulary, never a program/outcome/component name.
FINANCIAL_STATEMENT_LINE_ITEMS = {
    "employee benefits", "suppliers", "depreciation and amortisation",
    "depreciation/amortisation expenses", "finance costs", "write-down and "
    "impairment of assets", "grants", "subsidies", "personal benefits",
    "foreign exchange losses", "losses from asset sales", "other expenses",
    "interest", "dividends", "sales of goods and rendering of services",
    "sale of goods and rendering of services", "other revenue",
    "cash and cash equivalents", "receivables", "investments",
    "land, buildings and infrastructure", "property, plant and equipment",
    "computer software", "intangibles", "payables", "provisions",
    "employee provisions", "interest bearing liabilities", "contributed "
    "equity", "reserves", "retained earnings", "accumulated deficit",
    "trade creditors", "other payables", "prepayments", "inventories",
    "grants and subsidies", "goods and services", "accrued expenses",
}

TOTAL_SUBTOTAL = re.compile(
    r"^(?:Total|Sub-?total|Departmental Total|Administered Total|Net cash|"
    r"Net assets|Net increase|Net decrease|Net \(cost|Net cost|"
    r"Estimated (?:opening|closing) balance|Closing balance|Opening balance)\b",
    re.I,
)

NARRATIVE_LEAD = re.compile(r"^(?:plus|less|note|prepared on)\s*:?\s", re.I)

BARE_ACT_CITATION = re.compile(
    r"^[A-Z][A-Za-z0-9 '()\-,.]+\bAct\s+\d{4}(?:,\s*s\.?\s*\d+[A-Za-z()0-9]*)?\s*$"
)

OUTCOME_NUM = re.compile(r"(?:^|\s)Outcome\s+\d{1,2}\s*[:\-–—]", re.I)
PROGRAM_NUM = re.compile(r"(?:^|\s)Program\s+\d{1,2}(?:\.\d{1,2})?\s*[:\-–—]", re.I)
COMPONENT_NUM = re.compile(r"\d{1,2}\.\d{1,2}\.\d{1,2}\s*[\-–—]\s*Component", re.I)
# Only the two specific, verified-safe Defence Table 4b category names -
# matches scripts/ingest/extractors/pbs_programs_all.py's
# _clean_defence_program_label() after the database-hygiene milestone
# (Task 2) found every one of 26 real facts under the generic "Workforce"/
# "Operating"/"OPERATING"/"Operations" bare-keyword matches came from a
# completely unrelated table (never the genuine Key Cost Category table).
KEY_COST_CATEGORY = re.compile(
    r"^Key cost category\s*/\s*(Capability Acquisition Program|Capability Sustainment Program)\s*$",
    re.I,
)

MAX_JUSTIFIED_LENGTH = 180

CLASSES = (
    "program", "outcome", "component", "financial_statement_line",
    "table_header", "year_header", "unit_header", "subtotal", "total",
    "narrative_fragment", "malformed_concatenated_row", "unknown",
)
PUBLISHABLE_CLASSES = frozenset({"program", "outcome", "component"})


@dataclass
class Classification:
    classification: str
    publishable: bool
    rejection_reason: str | None
    signals: dict[str, Any] = field(default_factory=dict)


def _value_tokens(label: str) -> list[str]:
    return VALUE_TOKEN.findall(label)


def _year_tokens(label: str) -> list[str]:
    return YEAR_TOKEN.findall(label)


def _strip_year_and_unit_tokens(label: str) -> str:
    stripped = YEAR_TOKEN.sub(" ", label)
    stripped = UNIT_TOKEN.sub(" ", stripped)
    return re.sub(r"\s+", " ", stripped).strip()


def classify_label(raw_label: str) -> Classification:
    label = re.sub(r"\s+", " ", (raw_label or "")).strip()
    if not label:
        return Classification("unknown", False, "empty_label")

    value_tokens = _value_tokens(label)
    year_tokens = _year_tokens(label)
    signals = {
        "value_token_count": len(value_tokens),
        "year_token_count": len(year_tokens),
        "length": len(label),
    }

    # 1. Pure year/unit header: nothing left once year and unit tokens are
    #    stripped out (mission example: "000 2028-29 000").
    remainder = _strip_year_and_unit_tokens(label)
    if not remainder:
        if year_tokens:
            return Classification("year_header", False, "year_sequence_only", signals)
        return Classification("unit_header", False, "unit_marker_only", signals)

    # 2. Malformed concatenated row - the highest-confidence "definitely
    #    broken" signal: several dollar-value tokens embedded directly in
    #    the label text (multiple table columns flattened into one string),
    #    or a year/unit header glued onto financial-statement text, or a
    #    dangling numeric/punctuation tail, or the same accounting heading
    #    repeated (a page-continuation join), or an unjustifiably long label.
    if len(value_tokens) >= 3:
        return Classification(
            "malformed_concatenated_row", False, "three_or_more_embedded_value_tokens", signals
        )
    if BARE_NUMERIC_RUN.search(label):
        return Classification(
            "malformed_concatenated_row", False, "embedded_bare_numeric_run", signals
        )
    if year_tokens and ACCOUNTING_HEADINGS.search(label):
        return Classification(
            "malformed_concatenated_row", False, "year_header_glued_to_accounting_line", signals
        )
    if len(ACCOUNTING_HEADINGS.findall(label)) >= 2:
        return Classification(
            "malformed_concatenated_row", False, "repeated_accounting_heading", signals
        )
    # A numbering-like token (e.g. "1.5", "1.1") immediately followed by a
    # dash at the very end of the string, with nothing after it, is a
    # truncated row - the real title/value was cut off during extraction
    # (mission example: "... Administered payments 1.5 -"). Checked with no
    # value/year-token requirement, since the defining signal here is the
    # dangling dash itself, not the presence of a value elsewhere.
    if re.search(r"\b\d{1,2}(?:\.\d{1,2}){0,2}\s*[\-–—]\s*$", label):
        return Classification(
            "malformed_concatenated_row", False, "truncated_trailing_numeric_token", signals
        )
    if len(label) > MAX_JUSTIFIED_LENGTH:
        return Classification(
            "malformed_concatenated_row", False, "exceeds_justified_max_length", signals
        )

    # 3. Known program/outcome/component numbering patterns - checked ahead
    #    of the generic accounting-heading check below, since a real
    #    component/program description very often legitimately contains a
    #    qualifying phrase like "Annual administered expenses" without
    #    being a bare table-header row (e.g. "1.5.6 - Component 6 (Carer
    #    Adjustment Payment) Annual administered expenses"). Explicit
    #    numbering is stronger, more specific evidence than a single
    #    heading keyword appearing anywhere in a longer sentence.
    if OUTCOME_NUM.search(label):
        return Classification("outcome", True, None, signals)
    if COMPONENT_NUM.search(label):
        return Classification("component", True, None, signals)
    if PROGRAM_NUM.search(label) or KEY_COST_CATEGORY.match(label):
        return Classification("program", True, None, signals)
    # A "Key cost category / X" label whose X is not one of the two
    # whitelisted names must be rejected explicitly here - falling through
    # to the generic default-accept rule below would silently re-accept it
    # (a bare capitalised word like "Workforce" or "Operating" passes that
    # rule easily), which is exactly the bug this check exists to close.
    if re.match(r"^Key cost category\s*/", label, re.I):
        return Classification(
            "unknown", False, "key_cost_category_not_in_verified_whitelist", signals
        )

    # 4. Narrative fragments: lowercase-led continuations, or a bare
    #    legislative Act citation with nothing else attached. Checked ahead
    #    of the accounting-heading/vocabulary checks below since a "plus:"/
    #    "less:" continuation is strong, unambiguous evidence regardless of
    #    which accounting words happen to follow it.
    lowered = remainder.lower().strip(" -–—:")
    if NARRATIVE_LEAD.match(label):
        return Classification("narrative_fragment", False, "narrative_continuation_lead", signals)
    if label[:1].islower():
        return Classification("narrative_fragment", False, "starts_lowercase", signals)
    if BARE_ACT_CITATION.match(label) and len(label) < 60:
        return Classification("narrative_fragment", False, "bare_legislative_citation", signals)
    bare_generic = lowered in {"other", "gains", "other gains", "losses", "n.e.c.", "nec"}
    if bare_generic:
        # "- Other" is reviewed separately per the mission - do not reject
        # every "Other" row automatically, but a BARE "Other" with no
        # numbering or portfolio-specific qualifier attached is an orphaned
        # fragment, not evidence of a legitimate source category.
        return Classification(
            "narrative_fragment", False, "bare_generic_term_no_supporting_context", signals
        )

    # 5. Total / subtotal lines - checked before the generic accounting-
    #    heading check below since "Total expenses" / "Net cash from ..."
    #    is a more specific, intentional signal than a bare heading keyword
    #    match.
    if TOTAL_SUBTOTAL.match(label):
        cls = "total" if re.match(r"^Total\b", label, re.I) else "subtotal"
        return Classification(cls, False, "total_or_subtotal_line", signals)

    # 6. Table header: an accounting section heading with no real value
    #    tokens and no numbering match above - a header row extracted on
    #    its own, not yet glued to data.
    if ACCOUNTING_HEADINGS.search(label) and not value_tokens:
        return Classification("table_header", False, "accounting_heading_no_values", signals)

    # 7. Known financial-statement line items (curated AAS/GFS vocabulary) -
    #    real accounting rows, never a program/outcome/component name.
    if lowered in FINANCIAL_STATEMENT_LINE_ITEMS:
        return Classification("financial_statement_line", False, "known_line_item_vocabulary", signals)

    # 8. No defect signal fired and no explicit numbering either. Most
    #    genuine PBS program titles reach this point with no numbering
    #    prefix at all, because the extractor already strips bare numbering
    #    fragments shorter than 20 chars (see pbs_programs_all.py) - so a
    #    clean, well-shaped, reasonably long capitalised title with none of
    #    the rejection signals above is accepted as `program`; anything
    #    that still looks uncertain (short, or ambiguous shape) is left as
    #    `unknown` rather than guessed.
    if 8 <= len(remainder) <= MAX_JUSTIFIED_LENGTH and remainder[:1].isupper():
        return Classification("program", True, None, signals)

    return Classification("unknown", False, "no_confident_signal", signals)
