"""
Special-content filtering for AI-text detection.

Code, URLs, email addresses, citations, bibliography/reference sections,
mathematical formulas, tables, headings, metadata and page numbers should
never be highlighted as "AI-generated" merely because their linguistic
structure is unusual.  This module marks such spans so the segmenter can
exclude them from the analyzed windows.
"""

import re

_URL_RE = re.compile(
    r"(?:https?://|www\.)\S+", re.IGNORECASE
)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_CITATION_TRAILING_RE = re.compile(
    r"\([^)]*?(?:19|20)\d{2}[^)]*?\)\s*$"  # "(Smith, 2020)"
)
_CITATION_SQUARE_RE = re.compile(
    r"(?:^|\s)\[[\d,\-\s]+](?=\s|$)"  # "[1]"
)
_BIBLIO_HEADING_RE = re.compile(
    r"^(references|bibliography|works\s+cited|sources|further\s+[Rr]eading)\.?\s*$",
)
_PAGE_NUMBER_RE = re.compile(
    r"^\s*[-–—]?\s*\d{1,4}\s*[-–—]?\s*$"
)
_HEADING_RE = re.compile(
    r"^\s*(?:chapter|unit|section|module|part|week|lecture|appendix|lesson)"
    r"[\s\-.0-9]{1,12}[:.)]?\s+\S.*$",
    re.IGNORECASE,
)
# A heading that is just a label + optional number: "Chapter 1", "Unit 2",
# "Section 3".  These are full-string matches: a real sentence would keep
# going after the number and fail to match.
_HEADING_NUMBER_RE = re.compile(
    r"^\s*(?:chapter|unit|section|module|part|week|lecture|lesson|appendix)"
    r"[\s.\-]*(?:[0-9]+|[IVXLX]+)\s*\.?\s*$",
    re.IGNORECASE,
)
_SHORT_HEADING_RE = re.compile(
    r"^\s*([A-Z][A-Za-z&/-]*(?:\s+[A-Z][A-Za-z&/-]*){0,6})\s*[.:]?\s*$"
)
_CODE_LINE_RE = re.compile(
    r"(?:^\s*(?:def|class|import|from|return|if|else|elif|for|while|function|const|let|var|"
    r"public|private|void|int|str|echo|printf|SELECT|INSERT|UPDATE|DELETE|SET)\b)"
    r"|(?:=>|\{\s*\}|;\s*{)",
    re.IGNORECASE,
)
_FORMULA_RE = re.compile(
    r"(?:\d[\d,.\s]*[\u00d7\u00f7\*/^~]\s*\d)"      # 3*4, 12/3, 2^5
    r"|(?:\d[\d,.\s]*[+\-]\s*\d)"                   # 3+4, 12-7 (never a word hyphen)
    r"|(?:\b[a-zA-Z]\s*(?:=|<|>|≈|≠)\s*\d)"         # x=5, a > 3
    r"|(?:[√∫∑≤≥≠±∞πθλ][0-9a-zA-Z]*)"               # math symbols
    r"|(?:y\s*=\s*[0-9a-zA-Z+\-*/^]+)"              # y = mx + b
)

# Curated phrases that strongly mark scholarly/formal boilerplate.  A span
# dominated by these tokens is likely a template, not natural prose.
_STOP_HEADING_WORDS = {
    "abstract", "introduction", "objective", "objectives", "outline",
    "summary", "conclusion", "acknowledg", "keywords", "table", "figure",
    "fig.", "chapter", "index", "contents", "list of", "reference",
}


def is_url(text: str) -> bool:
    return bool(_URL_RE.search(text))


def is_email(text: str) -> bool:
    return bool(_EMAIL_RE.search(text))


def is_citation(text: str) -> bool:
    """True when the span looks like a citation/reference entry."""
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > 260:
        return False
    if _BIBLIO_HEADING_RE.match(stripped):
        return True
    if _CITATION_SQUARE_RE.search(stripped):
        return True
    if _CITATION_TRAILING_RE.search(stripped):
        return True
    # "Author, A. A. (2020). Title." bibliographic entries end with a
    # period but contain parentheses + year + another period.
    has_year_paren = re.search(r"\((?:19|20)\d{2}\)", stripped)
    if has_year_paren and stripped.count(".") >= 2:
        return True
    return False


def is_page_number(text: str) -> bool:
    return bool(_PAGE_NUMBER_RE.match(text or ""))


def is_heading(text: str) -> bool:
    """Short no-period line with capitalised words -> likely a heading."""
    stripped = (text or "").strip()
    if not stripped or len(stripped) > 90:
        return False
    if stripped.endswith((".", "!", "?")):
        return False
    if _HEADING_RE.match(stripped):
        return True
    if _HEADING_NUMBER_RE.match(stripped):
        return True
    if _SHORT_HEADING_RE.match(stripped):
        # Only treat as heading when it is short enough that a page
        # paragraph wouldn't look like this.
        words = stripped.split()
        if len(words) <= 7 and len(stripped) <= 60:
            return True
    return False


def is_code(text: str) -> bool:
    """Heuristic detection of code / SQL / config snippets."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return False
    code_hits = sum(1 for ln in lines if _CODE_LINE_RE.search(ln))
    if code_hits >= 2 and len(lines) <= 8:
        return True
    if code_hits >= max(2, len(lines) // 2):
        return True
    if sum(1 for ln in lines if re.search(r"[\{\}\[\];]", ln)) >= 3:
        return True
    return False


def is_formula(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    if len(re.findall(r"[0-9]", stripped)) > len(re.findall(r"[a-zA-Z]", stripped)):
        # Mostly numbers -> table cell or formula-like.
        return True
    matches = _FORMULA_RE.finditer(stripped)
    return sum(1 for _ in matches) >= 2


def is_table_row(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    return stripped.count("|") >= 2 or stripped.count("\t") >= 2


def is_metadata(text: str) -> bool:
    """Header/footer metadata like 'Page 3 of 10' or 'Mentora v1.0'."""
    stripped = (text or "").strip()
    if not stripped or len(stripped) > 60:
        return False
    if _PAGE_NUMBER_RE.match(stripped):
        return True
    if re.match(r"^\s*page\s*\d+(\s+of\s+\d+)?\s*$", stripped, re.IGNORECASE):
        return True
    if re.match(r"^\s*[A-Za-z ]+\s+v\d+(\.\d+)*\s*$", stripped):
        return True
    return False


def classify_span(text: str) -> str:
    """Classify a text span and return one of:
    "text" | "code" | "url" | "email" | "citation" | "table" |
    "formula" | "heading" | "page_number" | "metadata".

    Only "text" is analyzed; everything else is skipped (it is not a
    reliable basis for AI-detection claims).
    """
    stripped = (text or "").strip()
    if not stripped:
        return "text"  # nothing to say about empty spans

    if is_url(stripped):
        return "url"
    if is_email(stripped):
        return "email"
    if is_page_number(stripped):
        return "page_number"
    if is_metadata(stripped):
        return "metadata"
    if is_code(stripped):
        return "code"
    if is_table_row(stripped):
        return "table"
    if is_formula(stripped):
        return "formula"
    if is_citation(stripped):
        return "citation"
    if is_heading(stripped):
        return "heading"
    return "text"


def fraction_of_special_content(text: str) -> float:
    """Return the ratio of characters that classifiers treat as special.
    Used as a safeguard when computing the document-level score so that a
    reference-heavy or metadata-dense document is not scored as confident."""
    if not text or not text.strip():
        return 0.0
    total = len(text)
    if total == 0:
        return 0.0
    special = 0
    for line in re.split(r"\n+", text):
        kind = classify_span(line)
        if kind != "text":
            special += len(line)
    return min(1.0, special / total)