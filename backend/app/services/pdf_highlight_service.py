"""
Build a downloadable "highlighted" copy of an analyzed PDF.

Draws translucent red rectangles over every flagged region (bounding boxes
are already in PDF point space, origin bottom-left) using a reportlab
overlay page merged per original page with pypdf.  Pure-python, no native
dependencies.
"""

from io import BytesIO
from typing import Dict, List

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as rl_canvas

HIGHLIGHT_RGB = (1.0, 0.12, 0.12)
HIGHLIGHT_ALPHA = 0.55


def _get(item, key: str, default=None):
    """Read a field from either a dict or a Pydantic-style object."""
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _boxes_by_page(detections: List[dict], pages: List[dict]) -> Dict[int, List[dict]]:
    """Map 1-based page number -> list of detection boxes on that page."""
    known_pages = {_get(p, "page") for p in pages}
    grouped: Dict[int, List[dict]] = {}
    for detection in detections:
        page_no = _get(detection, "page")
        if page_no is None or page_no not in known_pages:
            continue
        raw_boxes = _get(detection, "boxes", []) or []
        boxes = [b for b in raw_boxes if b]
        if boxes:
            grouped.setdefault(int(page_no), []).extend(boxes)
    return grouped


def _dimensions(page, fallback: dict) -> tuple:
    """Return (width, height) of a pypdf page in points."""
    try:
        mb = page.mediabox
        width = float(mb.width)
        height = float(mb.height)
        if width > 0 and height > 0:
            return width, height
    except Exception:
        pass
    try:
        return float(fallback.get("width")), float(fallback.get("height"))
    except (TypeError, AttributeError):
        return 612.0, 792.0


def build_highlighted_pdf(
    pdf_bytes: bytes,
    pages: List[dict],
    detections: List[dict],
) -> bytes:
    """
    Return a new PDF identical to ``pdf_bytes`` with each flagged region on
    each page outlined/highlighted in translucent red.

    ``pages`` and ``detections`` come from a stored `PdfDetectionResponse`
    (page dims + detection boxes in PDF point space).
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    boxes_by_page = _boxes_by_page(detections, pages)
    page_info = {_get(p, "page"): p for p in pages}

    for index, original_page in enumerate(reader.pages, start=1):
        boxes = boxes_by_page.get(index, [])
        if boxes:
            info = page_info.get(index, {})
            width, height = _dimensions(original_page, info)
            overlay_buffer = BytesIO()
            overlay = rl_canvas.Canvas(overlay_buffer, pagesize=(float(width), float(height)))
            overlay.setFillColorRGB(*HIGHLIGHT_RGB)
            overlay.setFillAlpha(HIGHLIGHT_ALPHA)
            for box in boxes:
                try:
                    x0 = float(_get(box, "x0", 0))
                    y0 = float(_get(box, "y0", 0))
                    x1 = float(_get(box, "x1", x0))
                    y1 = float(_get(box, "y1", y0))
                except (TypeError, ValueError):
                    continue
                box_width = max(x1 - x0, 0.0)
                box_height = max(y1 - y0, 0.0)
                if box_width <= 0 or box_height <= 0:
                    continue
                overlay.rect(x0, y0, box_width, box_height, stroke=0, fill=1)
            overlay.save()

            overlay_data = overlay_buffer.getvalue()
            if overlay_data:
                overlay_page = PdfReader(BytesIO(overlay_data)).pages[0]
                original_page.merge_page(overlay_page)
        writer.add_page(original_page)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()