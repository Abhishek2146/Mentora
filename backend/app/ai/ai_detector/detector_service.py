"""
Detector service: the composition root for the multi-signal pipeline.

Exposes two public entry points used by the API:

* ``analyze_text(text, result_id)`` -> TextDetectionResponse
* ``analyze_pdf(pages, ...)``       -> PdfDetectionResponse

Both run the same statistical pipeline (segmenting -> windows -> weak
signals -> banded scores -> stable spans), and map the internal results on
to the documented API schemas, attaching PDF bounding boxes when available.
"""

import logging
from typing import Dict, List, Optional

from app.ai.ai_detector.calibration import (
    DetectorThresholds,
    band_for_score,
    confidence_from_reliability,
    label_for_score,
    label_description,
    short_document_advice,
)
from app.ai.ai_detector.model_detector import get_model_detector, model_blend_weight
from app.ai.ai_detector.schemas import (
    DetectionBox,
    DetectionDistribution,
    DetectionSignal,
    DetectionSpan,
    PdfDetectionResponse,
    PdfPage,
    TextDetectionResponse,
)
from app.ai.ai_detector.scoring import DocumentAnalysis, analyze_document
from app.core.config import settings

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "AI-text detection is probabilistic, not proof of authorship. Results "
    "measure writing characteristics that are statistically more common in "
    "AI-generated text; they cannot prove that a human did or did not write "
    "a document."
)


def build_thresholds() -> DetectorThresholds:
    return DetectorThresholds(
        low=float(settings.AI_DETECTION_LOW_THRESHOLD),
        medium=float(settings.AI_DETECTION_MEDIUM_THRESHOLD),
        high=float(settings.AI_DETECTION_HIGH_THRESHOLD),
        min_words=int(settings.AI_DETECTION_MIN_WORDS),
    )


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------

def _round(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _span_to_schema(span, page_offset: Optional[int]) -> DetectionSpan:
    signals = [
        DetectionSignal(
            name=s.name,
            explanation=s.explanation,
            value=_round(s.score),
        )
        for s in span.signals
    ]
    return DetectionSpan(
        text=span.text,
        start=span.start,
        end=span.end,
        confidence=_round(span.confidence),
        label=span.label,
        signals=signals,
        page=page_offset if page_offset is not None else span.page,
    )


def _summary(analysis: DocumentAnalysis) -> str:
    if analysis.insufficient_text:
        return "Text is too short or contains too little analyzable prose for a reliable verdict."
    dist = analysis.distribution
    ai = dist.get("ai_like", 0.0)
    uncertain = dist.get("uncertain", 0.0)
    human = dist.get("human", 0.0)
    label = label_description(analysis.label)
    if ai >= 0.6:
        verdict = (
            f"{ai * 100:.0f}% of analyzed words resemble generated prose; "
            f"the document shows {label.lower()} across coherent spans."
        )
    elif ai >= 0.25:
        verdict = (
            f"A mixed pattern: {human * 100:.0f}% of words look human-written "
            f"while {ai * 100:.0f}% show AI-typical signals."
        )
    else:
        verdict = (
            f"{human * 100:.0f}% of analyzed words show natural human "
            "writing characteristics."
        )
    return verdict


def _blend_with_model(analysis: DocumentAnalysis, t: DetectorThresholds) -> DocumentAnalysis:
    """Optionally shift the document score towards an ML model consensus.

    Disabled by default (see model_detector).  Only *document-level* score
    is affected; spans stay purely statistical so results remain explainable.
    """
    blend = model_blend_weight()
    detector = get_model_detector()
    if not (detector.enabled and blend > 0) or not analysis.spans:
        return analysis
    texts = [s.text for s in analysis.spans]
    probs = detector.predict_windows(texts)
    if not probs:
        return analysis
    model_avg = sum(probs) / len(probs)
    new_score = _round(analysis.overall_score * (1.0 - blend) + model_avg * blend)
    analysis.overall_score = new_score
    analysis.label = label_for_score(new_score, t)
    logger.info("Model detector blended: %s -> %s", analysis.overall_score, new_score)
    return analysis


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def analyze_text(text: str, result_id: str) -> TextDetectionResponse:
    t = build_thresholds()
    analysis = analyze_document(source=text, t=t)
    analysis = _blend_with_model(analysis, t)

    return TextDetectionResponse(
        result_id=result_id,
        overall_score=_round(analysis.overall_score),
        label=analysis.label,
        confidence=_round(analysis.confidence),
        analyzed_words=analysis.analyzed_words,
        summary=_summary(analysis),
        distribution=DetectionDistribution(
            ai_like=_round(analysis.distribution.get("ai_like", 0.0)),
            uncertain=_round(analysis.distribution.get("uncertain", 0.0)),
            human=_round(analysis.distribution.get("human", 0.0)),
        ),
        detections=[_span_to_schema(s, None) for s in analysis.spans],
        insufficient_text=analysis.insufficient_text,
        message=analysis.message or None,
        disclaimer=DISCLAIMER,
    )


def _word_window_boxes(page: PdfPage, start: int, end: int) -> List[DetectionBox]:
    """Build per-line bounding boxes for the words overlapping [start, end)."""
    overlapping = [
        w for w in page.words
        if w.start < end and w.end > start
    ]
    if not overlapping:
        return []
    overlapping.sort(key=lambda w: (w.y0, w.x0))
    # Group words that sit on the same visual line (y centre within 3pts).
    boxes: List[List] = []
    current: List = []
    for w in overlapping:
        y_center = (w.y0 + w.y1) / 2.0
        if current:
            prev = current[-1]
            prev_y = (prev.y0 + prev.y1) / 2.0
            same_line = abs(y_center - prev_y) <= 3.0
        else:
            same_line = True
        if not same_line:
            boxes.append(current)
            current = []
        current.append(w)
    if current:
        boxes.append(current)

    out: List[DetectionBox] = []
    for line_words in boxes:
        out.append(
            DetectionBox(
                x0=min(w.x0 for w in line_words),
                y0=min(w.y0 for w in line_words),
                x1=max(w.x1 for w in line_words),
                y1=max(w.y1 for w in line_words),
            )
        )
    return out


def analyze_pdf(
    pages: List[PdfPage],
    file_name: str,
    pdf_url: str,
    result_id: str,
    scanned: bool = False,
    extraction_warning: Optional[str] = None,
) -> PdfDetectionResponse:
    t = build_thresholds()

    page_analyses: List[DocumentAnalysis] = []
    for page in pages:
        analysis = analyze_document(source=page.text, t=t, page=page.page)
        page_analyses.append(analysis)

    total_words = sum(a.analyzed_words for a in page_analyses)
    if total_words > 0:
        overall = sum(
            a.overall_score * a.analyzed_words for a in page_analyses
        ) / total_words
    else:
        overall = 0.5

    distribution: Dict[str, float] = {"ai_like": 0.0, "uncertain": 0.0, "human": 0.0}
    for a in page_analyses:
        if not total_words:
            continue
        weight = a.analyzed_words / total_words
        for band in distribution:
            distribution[band] += a.distribution.get(band, 0.0) * weight

    purity = sum((1.0 - a.special_fraction) * a.analyzed_words for a in page_analyses) / max(1, total_words)
    dup = sum(a.duplicate_ratio * a.analyzed_words for a in page_analyses) / max(1, total_words)
    stability = sum(a.stability_ratio * a.analyzed_words for a in page_analyses) / max(1, total_words)

    insufficient, message = short_document_advice(total_words, t)
    if insufficient:
        label = "uncertain"
        overall = 0.5
        confidence = 0.05
    else:
        label = label_for_score(overall, t)
        confidence = confidence_from_reliability(
            total_words,
            purity=max(0.0, purity),
            duplicate_ratio=dup,
            stability_ratio=stability,
            overall_score=overall,
            t=t,
        )

    # Symbols: attach PDF boxes to each span using its page's word offsets.
    spans: List[DetectionSpan] = []
    for page, analysis in zip(pages, page_analyses):
        for span in analysis.spans:
            schema_span = _span_to_schema(span, page_offset=page.page)
            schema_span.boxes = _word_window_boxes(page, span.start, span.end)
            spans.append(schema_span)
    spans.sort(key=lambda s: ((s.page or 0), s.start))

    return PdfDetectionResponse(
        result_id=result_id,
        file_name=file_name,
        pdf_url=pdf_url,
        overall_score=_round(overall),
        label=label,
        confidence=_round(confidence),
        analyzed_words=total_words,
        summary=_summary_combined(
            total_words,
            overall,
            label,
            distribution,
            insufficient,
            message,
        ),
        distribution=DetectionDistribution(
            ai_like=_round(distribution.get("ai_like", 0.0)),
            uncertain=_round(distribution.get("uncertain", 0.0)),
            human=_round(distribution.get("human", 0.0)),
        ),
        detections=spans,
        pages=pages,
        scanned=scanned,
        extraction_warning=extraction_warning,
        insufficient_text=insufficient,
        message=message if insufficient else None,
        disclaimer=DISCLAIMER,
    )


def _summary_combined(
    total_words: int,
    overall: float,
    label: str,
    distribution: Dict[str, float],
    insufficient: bool,
    message: str,
) -> str:
    if insufficient:
        return (
            "PDF contains too little analyzable prose. " +
            (message or "See messages for details.")
        )
    ai = distribution.get("ai_like", 0.0)
    human = distribution.get("human", 0.0)
    label_note = label_description(label).lower()
    if ai >= 0.6:
        return (
            f"Across {total_words} analyzed words, {ai * 100:.0f}% resemble "
            f"generated prose and the document reads {label_note}."
        )
    if ai >= 0.25:
        return (
            f"Across {total_words} analyzed words the document is mixed: "
            f"{human * 100:.0f}% appear human-written and {ai * 100:.0f}% "
            "carry AI-typical signals."
        )
    return (
        f"Across {total_words} analyzed words the document reads {label_note} "
        f"({human * 100:.0f}% of words show natural human characteristics)."
    )