"""
PDF text + coordinate extraction for the AI detector.

Two strategies:

1. Embedded text (regular PDFs)
   Uses pypdf's ``extract_text(..., extraction_mode="layout", visitor_text=...)``
   callback, which reports (text run, x, y, font size) in PDF user space
   (origin at the bottom-left, units = points).  Runs are grouped into rows
   and every word carries a bounding box plus character offsets into the
   reconstructed page text, so the detector and the frontend share exactly
   the same offsets.

2. OCR fallback (scanned / image-based PDFs)
   If a page has no extractable text it is flagged as ``scanned``.  When
   pdf2image + pytesseract are available, the page is rendered and OCR'd
   with word-level boxes; boxes are converted from image-pixel space into
   PDF point space so the frontend can overlay them identically.  If OCR is
   unavailable the API returns an explicit warning instead of fabricating
   results.

Validation: malformed/empty PDFs and password-protected PDFs raise
``PdfExtractionError`` so the API can answer 400 instead of guessing.
"""

import io
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from pypdf import PdfReader

from app.ai.ai_detector.schemas import PdfPage, PdfWord

logger = logging.getLogger(__name__)

_PAGE_LINE_TOLERANCE = 2.0  # points
_GLYPH_WIDTH_RATIO = 0.5    # average glyph width as a fraction of font size


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be processed (malformed/empty/locked)."""


@dataclass
class PdfExtractionResult:
    pages: List[PdfPage]
    scanned: bool = False
    extraction_warning: Optional[str] = None


# --------------------------------------------------------------------------
# Embedded-text strategy
# --------------------------------------------------------------------------

def _words_from_visitor(page) -> List[PdfWord]:
    """Collect word boxes via pypdf's layout visitor callback."""
    runs: List[Tuple[float, float, Optional[float], str]] = []

    def visitor(text, cm, tm, font_dict, font_size):
        if not text:
            return
        runs.append((float(tm[4]), float(tm[5]), font_size, text))

    page.extract_text(
        visitor_text=visitor,
        orientations=(0, 90, 180, 270),
    )
    if not runs:
        return []

    # Split each run into whitespace-delimited tokens.  We do not know the
    # per-substring x offset, so each token keeps the run's origin offset by
    # its own accumulated length (an approximation; every box stays inside
    # its run, which keeps highlight alignment correct).
    tokens: List[Tuple[float, float, Optional[float], str]] = []
    for x, y, font_size, text in runs:
        parts = text.split()
        if not parts:
            continue
        cumulative = 0
        for part in parts:
            tokens.append((x + cumulative, y, font_size, part))
            cumulative += len(part) + 1
    if not tokens:
        return []

    # Reading order: top rows first (PDF bottom-left origin => higher y
    # first), then left-to-right within a row.
    tokens.sort(key=lambda t: (-t[1], t[0]))
    rows: List[List[Tuple[float, float, Optional[float], str]]] = []
    current: List[Tuple[float, float, Optional[float], str]] = []
    for tok in tokens:
        if current and abs(current[-1][1] - tok[1]) > _PAGE_LINE_TOLERANCE:
            rows.append(current)
            current = []
        current.append(tok)
    if current:
        rows.append(current)

    words: List[PdfWord] = []
    pos = 0
    for row in rows:
        if not row:
            continue
        row.sort(key=lambda t: t[0])
        for idx, (x, y, font_size, text) in enumerate(row):
            if idx > 0:
                pos += 1  # inter-word space in the reconstructed text
            start = pos
            end = pos + len(text)
            pos = end
            font = font_size if font_size and font_size > 0 else 10.0
            glyph = font * _GLYPH_WIDTH_RATIO
            words.append(
                PdfWord(
                    text=text,
                    start=start,
                    end=end,
                    x0=round(x, 2),
                    y0=round(y, 2),
                    x1=round(x + glyph * len(text), 2),
                    y1=round(y + font, 2),
                )
            )
        pos += 1  # row separator in the reconstructed text
    return words


def _page_text(words: List[PdfWord]) -> str:
    """Reconstruct page text using the exact rules the offsets were built
    from: a space between words on the same row, a newline between rows."""
    parts: List[str] = []
    last_y = None
    for w in words:
        if last_y is not None and abs(w.y0 - last_y) > _PAGE_LINE_TOLERANCE:
            parts.append("\n")
        elif last_y is not None:
            parts.append(" ")
        parts.append(w.text)
        last_y = w.y0
    return "".join(parts)


def _extract_embedded_pdf(content: bytes) -> Tuple[List[PdfPage], bool]:
    """Extract all pages.  Returns (pages, has_coordinates).  A page with no
    visitor words but readable plain text is still returned (text-only, no
    boxes) so detections remain possible without coordinate highlighting."""
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:  # pypdf raises various errors for junk input
        raise PdfExtractionError(
            "The file could not be parsed as a PDF. It may be corrupted or "
            "not actually be a PDF."
        ) from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:  # pragma: no cover - defensive
            pass
        if reader.is_encrypted:
            raise PdfExtractionError(
                "This PDF is password-protected. Remove the password and "
                "upload it again."
            )

    if len(reader.pages) == 0:
        raise PdfExtractionError("The PDF contains no pages.")

    pages: List[PdfPage] = []
    has_coords = False
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
        except Exception:  # pragma: no cover - defensive
            width, height = 0.0, 0.0

        words = _words_from_visitor(page)
        if words:
            text = _page_text(words)
            has_coords = True
        else:
            # No coordinate stream, but maybe plain text layer exists.
            try:
                text = (page.extract_text() or "").strip()
            except Exception:  # pragma: no cover - defensive
                text = ""
            words = []
        pages.append(
            PdfPage(
                page=page_no,
                text=text,
                width=round(width, 2),
                height=round(height, 2),
                words=words,
                ocr=False,
            )
        )
    return pages, has_coords


# --------------------------------------------------------------------------
# OCR fallback strategy
# --------------------------------------------------------------------------

def _tesseract_cmd() -> str:
    try:
        from app.core.config import settings  # noqa: PLC0415

        return settings.TESSERACT_CMD or "tesseract"
    except Exception:  # pragma: no cover - defensive
        return "tesseract"


def _ocr_pdf(content: bytes, pages: List[PdfPage]) -> PdfExtractionResult:
    """Attempt OCR on scanned pages; returns a warning when unavailable."""
    try:
        from pdf2image import convert_from_bytes  # noqa: PLC0415
        import pytesseract  # noqa: PLC0415

        pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd()
    except Exception as exc:
        logger.warning("OCR unavailable: %s", exc)
        return PdfExtractionResult(
            pages=pages,
            scanned=True,
            extraction_warning=(
                "This PDF appears to be scanned / image-based. OCR is "
                "required to analyze its text, but OCR support is not "
                "configured on this server, so no text-based detection "
                "was performed."
            ),
        )

    try:
        images = convert_from_bytes(content, dpi=200)
    except Exception as exc:
        logger.warning("PDF rendering failed: %s", exc)
        return PdfExtractionResult(
            pages=pages,
            scanned=True,
            extraction_warning=(
                "This PDF appears to be scanned / image-based but could not "
                "be rendered for OCR on this server."
            ),
        )

    ocr_pages: List[PdfPage] = []
    for page_no, image in enumerate(images, start=1):
        if page_no > len(pages):
            break
        original = pages[page_no - 1]
        scale_x = original.width / image.width if image.width else 0.0
        scale_y = original.height / image.height if image.height else 0.0
        try:
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("tesseract failed: %s", exc)
            return PdfExtractionResult(
                pages=pages,
                scanned=True,
                extraction_warning=(
                    "This PDF appears to be scanned / image-based; OCR ran "
                    "but produced no readable text."
                ),
            )

        words: List[PdfWord] = []
        pos = 0
        texts = data.get("text", [])
        lefts = data.get("left", [0])[: len(texts)]
        tops = data.get("top", [0])[: len(texts)]
        widths = data.get("width", [0])[: len(texts)]
        heights = data.get("height", [0])[: len(texts)]
        confs = data.get("conf", [0])[: len(texts)]
        for i, raw in enumerate(texts):
            raw = (raw or "").strip()
            if not raw or not lefts[i] or int(confs[i] or 0) < 30:
                continue
            x0 = lefts[i] * scale_x
            x1 = (lefts[i] + widths[i]) * scale_x
            top_px = tops[i]
            bot_px = tops[i] + heights[i]
            # Top-left pixel origin -> PDF bottom-left point space.
            y1_pts = original.height - top_px * scale_y
            y0_pts = original.height - bot_px * scale_y
            start = pos
            end = pos + len(raw)
            pos = end + 1  # single space between OCR words
            words.append(
                PdfWord(
                    text=raw,
                    start=start,
                    end=end,
                    x0=round(x0, 2),
                    y0=round(y0_pts, 2),
                    x1=round(x1, 2),
                    y1=round(y1_pts, 2),
                )
            )
        ocr_pages.append(
            PdfPage(
                page=page_no,
                text=_page_text(words),
                width=original.width,
                height=original.height,
                words=words,
                ocr=True,
            )
        )
    return PdfExtractionResult(pages=ocr_pages or pages, scanned=True)


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def extract_pdf(content: bytes, filename: str = "") -> PdfExtractionResult:
    """Extract pages with text and word boxes from raw PDF bytes.

    Raises PdfExtractionError for malformed / empty / password-protected
    PDFs.  Returns PdfExtractionResult for analyzable documents (scanned
    PDFs fall back to OCR).
    """
    if not content or not content.strip():
        raise PdfExtractionError("The uploaded file is empty.")

    pages, has_coords = _extract_embedded_pdf(content)
    has_any_text = any(p.text.strip() for p in pages)

    if has_coords:
        return PdfExtractionResult(pages=pages, scanned=False)
    if has_any_text:
        # Text layer exists but no coordinates (unusual PDFs).
        return PdfExtractionResult(
            pages=pages,
            scanned=False,
            extraction_warning=(
                "The PDF's text layer could be read without word coordinates, "
                "so results are shown as text only (no on-page highlights)."
            ),
        )
    return _ocr_pdf(content, pages)