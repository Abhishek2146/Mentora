"""
Pydantic schemas for the multi-signal AI-text detector.

These models describe the *public* shape of a detection result returned by
the API.  The detector itself works with plain dataclasses/dicts so the
scoring core stays pure and easy to test; only the service boundary converts
results into these schemas.

Confidence values are probabilities in [0, 1] (0 = human-like,
1 = strong AI-like).  Labels never claim certainty: we communicate
"potentially AI-generated", "strong AI-like linguistic signals",
"uncertain" or "likely human-written" because AI-text detection is
probabilistic.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


DetectionLabel = Literal[
    "likely_human",
    "uncertain",
    "potentially_ai_generated",
    "strong_ai_like_signals",
]


class DetectionSignal(BaseModel):
    """A single writing characteristic that influenced a score."""

    name: str = Field(..., min_length=1, max_length=80)
    explanation: str = Field(..., min_length=1, max_length=500)
    # Normalized strength of this signal in [0, 1] (0 = human-like,
    # 1 = very AI-like).  Used by the UI to show "which signal fired".
    value: float = Field(0.0, ge=0.0, le=1.0)


class DetectionBox(BaseModel):
    """A PDF bounding box in PDF point space (origin = bottom-left)."""

    x0: float
    y0: float
    x1: float
    y1: float


class DetectionSpan(BaseModel):
    """A span of text flagged as potentially AI-generated."""

    text: str = Field(..., min_length=1)
    # Character offsets relative to the analyzed page text (for PDFs) or
    # the normalized submitted text (for plain text input).
    start: int
    end: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    label: DetectionLabel
    signals: List[DetectionSignal] = Field(default_factory=list, max_length=8)
    # Page number (1-based).  None for plain-text input.
    page: Optional[int] = None
    # One or more bounding boxes when the span comes from a PDF.
    # A multi-line span may carry several boxes.
    boxes: List[DetectionBox] = Field(default_factory=list)


class DetectionDistribution(BaseModel):
    """Word-level distribution across the label bands (sums to ~1.0)."""

    ai_like: float = Field(0.0, ge=0.0, le=1.0)
    uncertain: float = Field(0.0, ge=0.0, le=1.0)
    human: float = Field(0.0, ge=0.0, le=1.0)


class DetectionBase(BaseModel):
    """Common fields shared by text and PDF detection responses."""

    result_id: str
    overall_score: float = Field(..., ge=0.0, le=1.0)
    label: DetectionLabel
    confidence: float = Field(..., ge=0.0, le=1.0)
    analyzed_words: int = Field(..., ge=0)
    summary: str
    distribution: DetectionDistribution
    detections: List[DetectionSpan] = Field(default_factory=list)
    insufficient_text: bool = False
    message: Optional[str] = None
    disclaimer: str = "AI-text detection is probabilistic, not proof of authorship."


class TextDetectionResponse(DetectionBase):
    """Result for manually entered / pasted text."""


class PdfWord(BaseModel):
    """A word on a PDF page together with its char offsets and box."""

    text: str
    start: int
    end: int
    x0: float
    y0: float
    x1: float
    y1: float


class PdfPage(BaseModel):
    """Extracted page text plus coordinates for highlight mapping."""

    page: int
    text: str
    # Page dimensions in points; the frontend uses them to scale boxes.
    width: float
    height: float
    words: List[PdfWord] = Field(default_factory=list)
    ocr: bool = False


class PdfDetectionResponse(DetectionBase):
    """Result for an uploaded PDF document."""

    file_name: str
    pdf_url: str
    pages: List[PdfPage] = Field(default_factory=list)
    scanned: bool = False
    extraction_warning: Optional[str] = None