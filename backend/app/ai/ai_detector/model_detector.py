"""
Optional model-based detector.

The statistical pipeline works offline and is the default.  When a small
text-classification model is configured (AI_DETECTOR_MODEL_ENABLED=true and
AI_DETECTOR_MODEL_NAME set), windows can also be scored with the model and
the two scores are blended.  Models are loaded lazily and cached once per
process; nothing is downloaded or loaded at import time, so the app keeps
starting instantly.
"""

import logging
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_blend_weight_key = "ai_detector_model_blend_weight"


class ModelDetector:
    """Adapter over a HuggingFace text-classification model (optional)."""

    def __init__(self) -> None:
        self._pipeline = None

    @property
    def enabled(self) -> bool:
        return bool(
            getattr(settings, "AI_DETECTOR_MODEL_ENABLED", False)
            and getattr(settings, "AI_DETECTOR_MODEL_NAME", "")
        )

    def _load(self):
        if self._pipeline is not None:
            return self._pipeline
        from transformers import pipeline  # heavy import, only when enabled

        self._pipeline = pipeline(
            "text-classification",
            model=settings.AI_DETECTOR_MODEL_NAME,
            truncation=True,
        )
        logger.info("AI detector model loaded: %s", settings.AI_DETECTOR_MODEL_NAME)
        return self._pipeline

    def predict_windows(self, window_texts: List[str]) -> Optional[List[float]]:
        """Return per-window AI probability in [0,1] or None if disabled."""
        if not self.enabled or not window_texts:
            return None
        try:
            pipe = self._load()
            results = pipe(window_texts, batch_size=8)
            out: List[float] = []
            for res in results:
                label = res[0]["label"].lower()
                score = res[0]["score"]
                # transformers gives a label like 'AI' or 'Human'; convert.
                is_ai = "ai" in label or "generated" in label or "machine" in label
                out.append(score if is_ai else 1.0 - score)
            return out
        except Exception as exc:  # pragma: no cover - infra dependent
            logger.warning("Model detector failed, falling back: %s", exc)
            return None


_model_detector = None


def get_model_detector() -> ModelDetector:
    global _model_detector
    if _model_detector is None:
        _model_detector = ModelDetector()
    return _model_detector


def model_blend_weight() -> float:
    """How much the model result shifts the statistical score (0 = off)."""
    return float(getattr(settings, "AI_DETECTOR_MODEL_BLEND_WEIGHT", 0.0))