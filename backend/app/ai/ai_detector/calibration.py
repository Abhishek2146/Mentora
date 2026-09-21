"""
Score banding / calibration for the AI detector.

Confidence is communicated as bands, never as a false-precision "100% AI":
    [0.00, 0.29]  likely_human
    [0.30, 0.59]  uncertain
    [0.60, 0.79]  potentially_ai_generated
    [0.80, 1.00]  strong_ai_like_signals

The band edges are configurable at runtime (AI_DETECTION_*_THRESHOLD env
vars) but always keep the same semantics.
"""

from dataclasses import dataclass
from typing import Dict, Tuple

from app.ai.ai_detector.schemas import DetectionLabel


@dataclass(frozen=True)
class DetectorThresholds:
    """Threshold configuration for the statistical detector."""

    low: float = 0.30      # below this -> likely_human band
    medium: float = 0.60   # at/above this -> "AI-like" territory
    high: float = 0.80     # at/above this -> strong AI-like band
    min_words: int = 40    # below this we refuse to make confident claims


BAND_LABELS: Dict[str, str] = {
    "likely_human": "Likely human-written",
    "uncertain": "Uncertain",
    "potentially_ai_generated": "Potentially AI-generated",
    "strong_ai_like_signals": "Strong AI-like signals",
}


def label_for_score(score: float, t: DetectorThresholds) -> DetectionLabel:
    """Map a [0,1] score to its public label band."""
    if score < t.low:
        return "likely_human"
    if score < t.medium:
        return "uncertain"
    if score < t.high:
        return "potentially_ai_generated"
    return "strong_ai_like_signals"


def band_for_score(score: float, t: DetectorThresholds) -> str:
    """Three-way band used for the word-level distribution:
    'ai_like' | 'uncertain' | 'human'."""
    if score >= t.medium:
        return "ai_like"
    if score >= t.low:
        return "uncertain"
    return "human"


def analyze_required_sentences(sentences_count: int, t: DetectorThresholds) -> bool:
    """Whether there is enough prose to make a reliable claim."""
    return sentences_count >= 2


def label_description(label: DetectionLabel) -> str:
    return BAND_LABELS.get(label, "Uncertain")


def confidence_from_reliability(
    analyzed_words: int,
    purity: float,
    duplicate_ratio: float,
    stability_ratio: float,
    overall_score: float,
    t: DetectorThresholds,
) -> float:
    """Confidence in the *label*, independent of the score itself.

    - More words (>~300) -> higher reliability.
    - High fraction of non-prose special content lowers confidence.
    - High duplicated-text ratio lowers confidence.
    - If few of the scored windows agree, the signal is murky.
    - A score near a band edge (e.g. 0.31 vs LOW_THRESHOLD) lowers the
      confidence in the verdict, because tiny noise could flip the band.
    Confidence is capped at 0.92; we never report near-certain labels.
    """
    size_factor = min(1.0, analyzed_words / 300.0) if analyzed_words > 0 else 0.0
    agreement_factor = 0.2 + 0.8 * stability_ratio
    reliability = 0.5 * size_factor + 0.5 * agreement_factor

    edges = sorted({t.low, t.medium, t.high})
    if edges:
        margin = min(abs(overall_score - edge) for edge in edges)
        margin_factor = min(1.0, 0.30 + (margin / 0.20) * 0.70)
    else:
        margin_factor = 0.5

    confidence = (
        0.10
        + 0.82 * reliability * purity * (1.0 - duplicate_ratio) * margin_factor
    )
    return max(0.0, min(0.92, confidence))


def short_document_advice(analyzed_words: int, t: DetectorThresholds) -> Tuple[bool, str]:
    """Return (insufficient, message) for documents too short to judge."""
    if analyzed_words < t.min_words:
        return True, (
            "Insufficient text for reliable detection. AI-text detection "
            "requires at least several sentences of natural prose; very "
            "short passages, isolated sentences, headings, lists, code, "
            "citations and tables cannot be judged reliably."
        )
    return False, ""