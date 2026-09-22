"""
Feature extraction for the AI-text detector.

Each feature is a *weak signal*: on its own it proves nothing, but combined
in a weighted ensemble it forms a stable, explainable estimate.  Features
operate on a window of several sentences (never single words) and return a
normalized score in [0, 1] where 0 = human-like and 1 = AI-like.

All mappings below are documented heuristics based on well-known stylometric
differences between statistical-language-model text and natural human prose
(higher lexical burstiness, wider sentence-length variation, less formulaic
transitions).  They are configurable via weights and thresholds, and the
evaluation script measures the effect of these choices on labeled samples.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import List, Optional

# Discourse markers / connective phrases that are over-represented in
# LLM-style expository writing.  Each entry is (phrase, weight).
_TRANSITIONS = [
    ("in conclusion", 1.2),
    ("consequently", 1.0),
    ("furthermore", 1.0),
    ("moreover", 1.0),
    ("additionally", 1.0),
    ("in addition", 1.0),
    ("therefore", 0.8),
    ("thus", 0.6),
    ("overall", 0.8),
    ("ultimately", 1.0),
    ("importantly", 1.0),
    ("notably", 1.0),
    ("it is important to note", 1.3),
    ("it should be noted", 1.3),
    ("it can be concluded", 1.3),
    ("plays a crucial role", 1.4),
    ("plays a vital role", 1.4),
    ("plays an essential role", 1.4),
    ("this highlights", 1.2),
    ("this demonstrates", 1.2),
    ("this underscores", 1.2),
    ("in summary", 1.2),
    ("as a result", 0.9),
    ("in today's world", 1.6),
    ("in the modern era", 1.6),
    ("in recent years", 0.8),
    ("one of the most important", 1.2),
    ("it is widely recognized", 1.3),
    ("it is essential that", 1.2),
    ("in essence", 1.3),
    ("the importance of", 0.8),
]

_TRANSITION_REGEXES = [
    (re.compile(re.escape(phrase), re.IGNORECASE), weight)
    for phrase, weight in _TRANSITIONS
]

# High-level scaffolding phrases found in LLM-style expository writing.
_SCAFFOLDING_PHRASES = [
    re.compile(r"\bin\s+today['’]?s?\s+(modern\s+)?(world|era|society|day(s)?)\b", re.IGNORECASE),
    re.compile(r"\bplays?\s+a\s+(crucial|vital|essential|key|significant)\s+role\b", re.IGNORECASE),
    re.compile(r"\bit\s+is\s+(important|essential|crucial|worth\s+noting|widely\s+recognized|"
               r"widely\s+acknowledged)\s+(to\s+note\s+that|that|to)\b", re.IGNORECASE),
    re.compile(r"\bcannot\s+be\s+overstated\b", re.IGNORECASE),
    re.compile(r"\b(highlights|underscores|demonstrates|illustrates)\s+the\s+(importance|significance|impact)\b", re.IGNORECASE),
    re.compile(r"\bthe\s+(importance|significance)\s+of\b", re.IGNORECASE),
    re.compile(r"\bin\s+(conclusion|summary|essence)\b", re.IGNORECASE),
    re.compile(r"\bin\s+an?\s+ever[- ]changing\s+landscape\b", re.IGNORECASE),
]

_DISCOURSE_OPENERS = (
    "furthermore", "moreover", "additionally", "therefore", "thus",
    "however", "consequently", "ultimately", "importantly", "notably",
    "overall", "hence", "meanwhile", "conversely",
)

# Markers of a *personal* human voice.  Modern language models still rarely
# use contractions, first-person references, or conversational filler; their
# near-total absence is a strong (if soft) AI signal, and their presence is a
# strong human signal.
_CONTRACTION_RE = re.compile(r"\b\w+'\w+\b")
_PERSONAL_RE = re.compile(
    r"\b(i|me|we|us|my|our|mine|you|your|yours)\b", re.IGNORECASE
)
_COLLOQUIAL_RE = re.compile(
    r"\b(sort of|kind of|kinda|actually|basically|honestly|pretty|really|"
    r"stuff|things|gonna|wanna|alright|anyway|somehow|maybe|huge|nice|"
    r"great|pretty much|a bit|a lot|by the way|to be honest)\b",
    re.IGNORECASE,
)


@dataclass
class Feature:
    """A computed signal with an explainable name."""

    name: str
    explanation: str
    score: float  # 0..1, higher = more AI-like
    weight: float  # contribution to the ensemble


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _linear_map(value: float, low_x: float, high_x: float, low_y: float, high_y: float) -> float:
    """Map value in [low_x, high_x] to [low_y, high_y], clamped."""
    if high_x == low_x:
        return _clip((low_y + high_y) / 2)
    t = (value - low_x) / (high_x - low_x)
    return _clip(low_y + t * (high_y - low_y))


def sentence_length_uniformity(sentence_word_counts: List[int], words: List[str]) -> Optional[Feature]:
    """Unusually uniform sentence lengths are common in generated prose."""
    if len(sentence_word_counts) < 3:
        return None
    mean_len = mean(sentence_word_counts)
    if mean_len <= 0:
        return None
    std = pstdev(sentence_word_counts)
    cv = std / mean_len  # coefficient of variation
    # cv < 0.25 => very uniform; cv > 0.7 => naturally varied
    score = _linear_map(cv, 0.25, 0.75, 0.92, 0.08)
    # Neutral when the average sentence is extremely short (list-like text).
    if mean_len < 8:
        score = 0.5
    return Feature(
        name="Uniform sentence rhythm",
        explanation=(
            f"Sentence lengths are unusually consistent (coefficient of "
            f"variation {cv:.2f}), which generated text tends to exhibit more "
            f"than natural drafting."
        ),
        score=score,
        weight=1.6,
    )


def personal_voice(window_text: str, words: List[str]) -> Optional[Feature]:
    """Signal derived from the *absence* of a personal human voice.

    Contractions, first/second-person pronouns and conversational filler are
    pervasive in natural personal drafting and almost entirely absent in
    machine-generated expository prose.  This is one of the most reliable
    separators for modern (natural-sounding) LLM output that no longer leans
    on classic scaffold phrases.
    """
    if not words:
        return None
    markers = (
        len(_CONTRACTION_RE.findall(window_text))
        + len(_PERSONAL_RE.findall(window_text))
        + len(_COLLOQUIAL_RE.findall(window_text))
    )
    density = markers / len(words)
    # The map is deliberately asymmetric: even two or three stray pronouns in
    # a 60-word window (density ~0.05) are still characteristic of machine
    # prose and must NOT zero this signal (that used to let a single "we" or
    # "our" collapse an entire AI window through the resolution gate below).
    # Only genuinely personal text (density >= ~0.12, real contractions,
    # first-person narration, informal filler) drops the score into human
    # territory.
    score = _linear_map(density, 0.12, 0.04, 0.2, 0.88)
    return Feature(
        name="Absence of personal voice",
        explanation=(
            f"Only {markers} personal/colloquial markers across {len(words)} "
            "analysed words (density {:.3f}). Natural drafting almost always "
            "carries some contractions, first-person phrasing, or informal "
            "flourishes; generated expository text does not.".format(density)
        ),
        score=score,
        weight=1.8,
    )


def repeated_ngrams(words: List[str], n: int = 4) -> Optional[Feature]:
    if len(words) < n + 3:
        return None
    grams = [tuple(words[i: i + n]) for i in range(len(words) - n + 1)]
    total = len(grams)
    if total == 0:
        return None
    unique = len(set(grams))
    repeat_rate = (total - unique) / total
    score = _clip(repeat_rate * 3.2)
    return Feature(
        name="Repeated phrasing",
        explanation=(
            f"{total - unique} of {total} {n}-word sequences recur exactly, "
            "which appears more often in generated than natural text."
        ),
        score=score,
        weight=0.7,
    )


def transition_density(window_text: str) -> Optional[Feature]:
    hits = 0.0
    for regex, weight in _TRANSITION_REGEXES:
        hits += weight * len(regex.findall(window_text))
    words = len(re.findall(r"\S+", window_text))
    if words < 5:
        return None
    density = hits / words
    score = _linear_map(density, 0.008, 0.06, 0.1, 0.92)
    return Feature(
        name="Formulaic transitions",
        explanation=(
            "Formal connective phrases occur at a density of "
            f"{density:.3f} per word, a pattern more typical of template "
            "writing than natural prose."
        ),
        score=score,
        weight=1.1,
    )


def start_word_uniformity(sentence_word_counts: List[int], sentence_first_words: List[str]) -> Optional[Feature]:
    """Low variety in sentence openings (e.g. The/This/It) -> template style."""
    if len(sentence_first_words) < 3:
        return None
    counts = Counter(sentence_first_words)
    total = len(sentence_first_words)
    entropy = -sum(
        (c / total) * math.log2(c / total) for c in counts.values()
    )
    max_entropy = math.log2(total) if total > 1 else 0.0
    normalized = entropy / max_entropy if max_entropy else 1.0
    score = _clip(1.0 - normalized)
    return Feature(
        name="Uniform sentence openings",
        explanation=(
            f"Sentence openings repeat heavily (normalized entropy "
            f"{normalized:.2f}), giving the passage a mechanical rhythm."
        ),
        score=score,
        weight=0.9,
    )


def parallel_structures(sentence_first_bigrams: List[str]) -> Optional[Feature]:
    """Repeated two-word openings across sentences signal parallel templates."""
    if len(sentence_first_bigrams) < 3:
        return None
    counts = Counter(sentence_first_bigrams)
    repeats = sum(c - 1 for c in counts.values() if c > 1)
    fraction = repeats / max(1, len(sentence_first_bigrams))
    score = _clip(fraction * 2.6)
    return Feature(
        name="Parallel sentence structure",
        explanation=(
            f"{repeats} sentence openings share the same leading two-word "
            "pattern, which generated prose uses more consistently."
        ),
        score=score,
        weight=1.1,
    )


def medium_length_regularity(sentence_word_counts: List[int]) -> Optional[Feature]:
    """A large fraction of sentences in the 15-35 word band => regularity."""
    if len(sentence_word_counts) < 3:
        return None
    in_band = sum(1 for c in sentence_word_counts if 15 <= c <= 35)
    fraction = in_band / len(sentence_word_counts)
    score = _linear_map(fraction, 0.35, 0.9, 0.15, 0.85)
    return Feature(
        name="Uniform clause length",
        explanation=(
            f"{in_band} of {len(sentence_word_counts)} sentences fall in a "
            "narrow mid-length band, suggesting template-composed prose."
        ),
        score=score,
        weight=0.9,
    )


def scaffolding_ratio(
    window_text: str,
    sentence_first_words: List[str],
) -> Optional[Feature]:
    """Fraction of sentences built from formulaic scaffolding.

    Counts sentences that open with a discourse connector, or that contain
    any layout-of-an-essay template (openers like "in today's world", "plays
    a crucial role", "cannot be overstated", "highlights the importance").
    A high ratio of such scaffolding is a hallmark of generated essays.
    """
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", window_text) if s.strip()]
    if len(sentences) < 3:
        return None
    templated = 0
    first_words = [w.lower() for w in sentence_first_words]
    for first in first_words:
        if first in _DISCOURSE_OPENERS:
            templated += 1
    for s in sentences:
        for regex in _SCAFFOLDING_PHRASES:
            if regex.search(s):
                templated += 1
                break
    ratio = templated / len(sentences)
    score = _linear_map(ratio, 0.15, 0.65, 0.05, 0.95)
    return Feature(
        name="Formulaic scaffolding",
        explanation=(
            f"{templated} of {len(sentences)} sentences use essay templates "
            f"or discourse connectors (ratio {ratio:.2f}), which generated "
            "expository text relies on far more than natural drafting."
        ),
        score=score,
        weight=1.5,
    )


def extract_window_features(
    window_text: str,
    sentence_word_counts: List[int],
    sentence_first_words: List[str],
    sentence_first_bigrams: List[str],
) -> List[Feature]:
    """Compute all weak signals for one window of text."""
    words = re.findall(r"\b[\w'’_-]+\b", window_text.lower())
    features: List[Feature] = []

    builders = [
        lambda: sentence_length_uniformity(sentence_word_counts, words),
        lambda: personal_voice(window_text, words),
        lambda: repeated_ngrams(words),
        lambda: transition_density(window_text),
        lambda: start_word_uniformity(sentence_word_counts, sentence_first_words),
        lambda: parallel_structures(sentence_first_bigrams),
        lambda: medium_length_regularity(sentence_word_counts),
        lambda: scaffolding_ratio(window_text, sentence_first_words),
    ]
    for builder in builders:
        try:
            feature = builder()
        except (ValueError, ZeroDivisionError):  # pragma: no cover - defensive
            feature = None
        if feature is not None:
            features.append(feature)
    return features


def top_features(features: List[Feature], limit: int = 8) -> List[Feature]:
    """Most influential features, ordered by |score - 0.5| * weight."""
    ranked = sorted(
        features,
        key=lambda f: abs(f.score - 0.5) * f.weight,
        reverse=True,
    )
    return ranked[:limit]