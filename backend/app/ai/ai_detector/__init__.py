"""
Multi-signal statistical AI-text detector.

Package layout:
    content_filter     – excludes code/URLs/citations/tables/headings...
    text_segmenter     – sentence splitting + overlapping windows
    feature_extractor  – weak writing-style signals
    scoring            – window/sentence/spans + document score
    calibration        – score bands and confidence calibration
    model_detector     – optional ML model adapter (off by default)
    detector_service   – composition root exposed to the API
    schemas            – public API response models
"""

from app.ai.ai_detector.detector_service import analyze_pdf, analyze_text
from app.ai.ai_detector.schemas import (
    PdfDetectionResponse,
    TextDetectionResponse,
)

__all__ = [
    "analyze_text",
    "analyze_pdf",
    "PdfDetectionResponse",
    "TextDetectionResponse",
]