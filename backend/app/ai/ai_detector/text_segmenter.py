"""
Sentence segmentation and sliding-window construction for the AI detector.

Detection is performed on windows of several consecutive sentences with
overlap (e.g. sentences 1-5, 3-7, 5-9) so that results are stable and not
dependent on arbitrary paragraph boundaries.  Each sentence carries its
character offsets so flagged windows can be mapped back to exact spans.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.ai.ai_detector.content_filter import classify_span

# Common abbreviations that end in "." but are not sentence boundaries.
_ABBREVIATIONS = frozenset(
    {
        "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc",
        "e.g", "i.e", "al", "fig", "no", "vol", "pp", "cf", "dept",
        "inc", "ltd", "co", "bros", "corp", "rev", "mt", "ft", "approx",
        "min", "max", "avg", "gen", "jan", "feb", "mar", "apr", "aug",
        "sep", "sept", "oct", "nov", "dec", "sec", "ch", "p",
    }
)

_WORD_RE = re.compile(r"[A-Za-z0-9'’_-]+", re.UNICODE)


@dataclass
class Sentence:
    """One sentence with offsets relative to its source text."""

    start: int
    end: int
    text: str
    kind: str = "text"  # classification from content_filter.classify_span
    words: List[str] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return len(self.words)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Sentence {self.start}:{self.end} kind={self.kind} words={self.word_count}>"


def tokenize_words(text: str) -> List[str]:
    """Lowercased word tokens used by the statistical features."""
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def iter_sentences(text: str):
    """Yield (start, end, sentence_text) tuples scanning ``text``.

    Handles common abbreviations, decimals, and initials so offsets stay
    stable and sentences are not split mid-abbreviation.  Newlines are
    treated as plain whitespace: headings/labels are excluded *before* this
    function runs (see ``segment_text``), because a wrapped paragraph line
    break must never split a real sentence.
    """
    n = len(text)
    if n == 0:
        return
    start = 0
    i = 0
    while i < n:
        ch = text[i]
        if ch in ".!?":
            if ch == ".":
                # Skip abbreviations: "Dr.", "e.g.", "3.14", "A."
                prev = text[max(start, i - 8): i]
                m = re.search(r"([A-Za-z]+)\s*$", prev)
                if m:
                    token = m.group(1).lower()
                    if token in _ABBREVIATIONS:
                        i += 1
                        continue
                # Single capital initial "A." / "J."
                if re.search(r"(?:^|\s)([A-Z])\.\s*$", prev) and i + 1 < n and not text[i + 1].islower():
                    i += 1
                    continue
                # Decimal number "3.14"
                if re.search(r"\d\s*$", prev) and i + 1 < n and text[i + 1].isdigit():
                    i += 1
                    continue

            # Only a real sentence end when followed by whitespace/quote/closing
            # bracket or the end of the string.
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt in " \t\n\r\"')\u201d\u2019\u201c\u2018]" or nxt == "":
                end = i + 1
                yield start, end, text[start:end]
                start = end
        i += 1
    if start < n:
        yield start, n, text[start:n]


_LINE_SPLIT_RE = re.compile(r"[^\r\n]*")


def _line_classes(text: str):
    """Iterate (line_start, line_end, kind) over the text's lines.

    Lines are classified with ``content_filter.classify_span`` so that
    headings / code / citations / URLs / tables never leak into prose.
    """
    pos = 0
    n = len(text)
    while pos <= n:
        m = _LINE_SPLIT_RE.match(text, pos)
        start = m.start()
        end = m.end()
        end = min(end, n)
        line = text[start:end]
        yield start, end, classify_span(line) if line.strip() else "text"
        pos = end + 1  # skip the \r or \n
        if pos == n + 1:
            break


def segment_text(text: str) -> List[Sentence]:
    """Split ``text`` into Sentence objects with offsets and kind flags.

    Headings / code / URLs / citations / tables are excluded *at the line
    level* (their lines form non-prose gaps).  Prose blocks are then split
    into sentences on terminal punctuation; wrapped paragraph lines merge
    into one sentence because newlines inside a prose block are whitespace.
    """
    sentences: List[Sentence] = []

    prose_start = None
    for line_start, line_end, kind in _line_classes(text):
        if kind == "text":
            if prose_start is None:
                prose_start = line_start
            continue
        # Non-prose line: close any open prose block BEFORE this line.
        if prose_start is not None:
            _append_prose_sentences(text, prose_start, line_start, sentences)
            prose_start = None
    if prose_start is not None:
        _append_prose_sentences(text, prose_start, len(text), sentences)

    return sentences


def _append_prose_sentences(
    text: str,
    start: int,
    end: int,
    out: List[Sentence],
) -> None:
    """Segment one contiguous prose block and append its sentences."""
    block = text[start:end]
    if not block.strip():
        return
    for s_start, s_end, raw in iter_sentences(block):
        words = tokenize_words(raw)
        if not words:
            continue
        # A sentence inside a prose block may still be special (a URL or a
        # citation embedded mid-paragraph): exclude it individually too.
        kind = classify_span(raw)
        if kind != "text":
            continue
        out.append(
            Sentence(
                start=start + s_start,
                end=start + s_end,
                text=raw,
                kind=kind,
                words=words,
            )
        )


def analyzeable_sentences(sentences: List[Sentence]) -> List[Sentence]:
    """Only natural-language sentences are suitable for detection."""
    return [s for s in sentences if s.kind == "text"]


@dataclass
class Window:
    """A sliding window of consecutive sentences."""

    index: int
    sentence_indexes: List[int]  # indexes into the full sentence list
    text: str
    word_count: int
    score: Optional[float] = None

    @property
    def sentence_count(self) -> int:
        return len(self.sentence_indexes)


def build_windows(
    sentences: List[Sentence],
    window_size: int = 4,
    step: int = 2,
    min_window_words: int = 30,
) -> List[Window]:
    """
    Construct overlapping sentence windows.

    Only positions that begin a window are used; non-text (special) sentences
    are kept inside a window's span but do not prevent windows being built.
    Windows with too few analyzeable words are intentionally dropped so the
    detector never makes claims from code/references/titles.
    """
    windows: List[Window] = []
    idcs = list(range(len(sentences)))
    i = 0
    while i < len(sentences):
        chunk = idcs[i: i + window_size]
        if len(chunk) < 1:
            break
        words = sum(
            (sentences[c].words for c in chunk if sentences[c].kind == "text"), []
        )
        if len(words) >= max(1, min_window_words):
            text = " ".join(sentences[c].text for c in chunk)
            windows.append(
                Window(
                    index=len(windows),
                    sentence_indexes=list(chunk),
                    text=text,
                    word_count=len(words),
                )
            )
        i += step
    # Always include the tail window so the very last sentences are scored
    # even when the stride would skip them.
    if len(sentences) and (not windows or windows[-1].sentence_indexes[-1] < len(sentences) - 1):
        chunk = idcs[-window_size:]
        words = sum(
            (sentences[c].words for c in chunk if sentences[c].kind == "text"), []
        )
        if len(words) >= max(1, min_window_words):
            windows.append(
                Window(
                    index=len(windows),
                    sentence_indexes=list(chunk),
                    text=" ".join(sentences[c].text for c in chunk),
                    word_count=len(words),
                )
            )
    return windows