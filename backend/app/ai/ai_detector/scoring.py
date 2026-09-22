"""
Scoring, span aggregation and document-level scoring.

Window / sentence scoring
-------------------------
A window of ~4 consecutive sentences receives a score in [0,1] = weighted
mean of its weak-signal features.  Because windows overlap (step 2), each
sentence ends up covered by several windows; the *sentence score* is the
mean of the windows that contain it, and its *consistency* is the fraction
of those windows that agree (score >= AI_DETECTION_MEDIUM_THRESHOLD).

Spans
-----
A sentence is *flagged* when its score is >= HIGH, or when it sits in
[MEDIUM, HIGH) with >=80% window consistency.  Watching the banded score
alone is not enough: if window1 = 0.73 and window2 = 0.31 both touch a
region, the sentences there are only flagged when the surrounding windows
agree, so we never over-highlight a whole block from one hot window.

Merging
-------
Adjacent flagged sentences are merged into a single detection span ONLY if
they are consecutive; a low-scoring sentence in the middle (0.74 / 0.25 /
0.71) always breaks the run into separate spans (or discards the middle).
Optional gap-merging is restricted to one short non-flagged sentence
(<= 6 words) when both neighbouring edges are strongly flagged.

Document score
--------------
overall_score = Σ(w_i * score_i) / Σ(w_i)
where each w_i is the *word count* of a stable window i (stability defined
below).  This is deliberately NOT "highlighted words / total words": a
document is judged by whole coherent windows, so a 200-word doc with one
20-word repetitive snippet cannot reach a strong band just by ratio trick.

A window is *stable* when at least half of the windows that overlap it
share its high/low side of the MEDIUM threshold.  Oscillating windows
(0.73 then 0.31) cancel each other out and are excluded from the mean; if
no window is stable the document is reported as "uncertain" (0.5).

Safeguards
----------
- Windows with too few prose words are never scored.
- Code/references/headings/tables/formulas are excluded before scoring.
- The confidence (not the score) is reduced when the text is short, dense
  in special content, or heavily duplicated.
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.ai.ai_detector.calibration import (
    DetectorThresholds,
    band_for_score,
    confidence_from_reliability,
    label_for_score,
    short_document_advice,
)
from app.ai.ai_detector.content_filter import fraction_of_special_content
from app.ai.ai_detector.feature_extractor import (
    Feature,
    extract_window_features,
    top_features,
)
from app.ai.ai_detector.text_segmenter import (
    Sentence,
    Window,
    analyzeable_sentences,
    build_windows,
    iter_sentences,
    segment_text,
)

MIN_SPAN_WORDS = 15  # merge only when the flagged run is a real paragraph
GAP_MERGE_MAX_WORDS = 6  # allow absorbing one tiny unflagged gap between runs
MIN_WINDOW_WORDS = 30


@dataclass
class DetectedSpan:
    """A merged run of flagged sentences."""

    start: int
    end: int
    text: str
    confidence: float  # word-weighted mean of constituent sentence scores
    label: str
    signals: List[Feature]
    sentence_indexes: List[int] = field(default_factory=list)
    word_count: int = 0
    page: Optional[int] = None


@dataclass
class DocumentAnalysis:
    """Result of the full detection pipeline over one unit of text."""

    source: str
    sentences: List[Sentence]
    analyzed_words: int
    spans: List[DetectedSpan]
    distribution: Dict[str, float]          # ai_like / uncertain / human
    overall_score: float
    label: str
    confidence: float
    insufficient_text: bool
    message: str
    duplicate_ratio: float = 0.0
    special_fraction: float = 0.0
    stability_ratio: float = 0.0
    warnings: List[str] = field(default_factory=list)


def _window_features(w: Window, sentences: List[Sentence]) -> List[Feature]:
    sub = [sentences[i] for i in w.sentence_indexes]
    prose = [s for s in sub if s.kind == "text"]
    counts = [s.word_count for s in prose]
    first_words = [s.words[0] if s.words else "" for s in prose]
    first_bigrams = [" ".join(s.words[:2]) for s in prose]
    return extract_window_features(
        w.text, counts, first_words, first_bigrams
    )


def _resolve_window_score(score: float, features: List[Feature]) -> float:
    """Nonlinear resolution on top of the weighted mean.

    The plain mean of many weak signals is skewed toward 0.5: absence of
    one family of markers always drags the total down.  When several
    *independent* AI-confirming signals agree strongly at once
    (very uniform rhythm + regular clause lengths + an almost total absence
    of personal voice), the window is polished template-like prose and should
    be treated as potentially generated even if scaffold phrases are missing.
    Conversely, prose with strong personal markers is capped low so a single
    neutral window can never push a clearly human passage up.
    """
    by_name = {f.name: f.score for f in features}
    rhythm = by_name.get("Uniform sentence rhythm")
    voice = by_name.get("Absence of personal voice")
    clause = by_name.get("Uniform clause length")
    scaffold = by_name.get("Formulaic scaffolding", 0.0)
    if None not in (rhythm, voice, clause):
        # Uniform rhythm + no personal voice + mid-length regularity is NOT
        # enough on its own: dry but genuinely human academic prose shares
        # all three (cf. FORMAL_HUMAN-style passages).  Only *boost* the
        # window toward "potentially AI-generated" when there is explicit
        # essay-template evidence (scaffold/connector phrases) on top.
        if (
            rhythm >= 0.75
            and voice >= 0.55
            and (clause >= 0.5 or rhythm >= 0.92)
            and scaffold >= 0.35
        ):
            return max(score, 0.68)
        if voice <= 0.35:
            return min(score, 0.3)
    return score


def _flag_sentences(
    sentences: List[Sentence],
    sent_scores: Dict[int, Tuple[float, float]],
    t: DetectorThresholds,
) -> Dict[int, bool]:
    flagged: Dict[int, bool] = {}
    for i, s in enumerate(sentences):
        if s.kind != "text" or i not in sent_scores:
            flagged[i] = False
            continue
        mean_score, consistency = sent_scores[i]
        if mean_score >= t.high:
            flagged[i] = True
        elif t.medium <= mean_score < t.high and consistency >= 0.8:
            flagged[i] = True
        else:
            flagged[i] = False
    return flagged


def _runs_of_flagged(flagged: Dict[int, bool], sentences: List[Sentence]) -> List[List[int]]:
    runs: List[List[int]] = []
    current: List[int] = []
    for i in range(len(sentences)):
        if flagged.get(i):
            current.append(i)
        else:
            if current:
                runs.append(current)
                current = []
    if current:
        runs.append(current)
    return runs


def _merge_gaps(
    runs: List[List[int]],
    sentences: List[Sentence],
    sent_scores: Dict[int, Tuple[float, float]],
    t: DetectorThresholds,
) -> List[List[int]]:
    """Absorb a single tiny (<=6 word) unflagged sentence between two strongly
    flagged runs so a minor connector does not visually fragment an otherwise
    continuous passage.  Never merges across an ordinary low-scoring sentence."""
    if len(runs) < 2:
        return runs
    merged = [list(runs[0])]
    for nxt in runs[1:]:
        prev = merged[-1]
        gap = list(range(prev[-1] + 1, nxt[0]))
        if len(gap) == 1:
            g = sentences[gap[0]]
            prev_edge = sent_scores.get(prev[-1], (0.0, 0.0))[0]
            nxt_edge = sent_scores.get(nxt[0], (0.0, 0.0))[0]
            if (
                g.kind == "text"
                and g.word_count <= GAP_MERGE_MAX_WORDS
                and prev_edge >= t.high
                and nxt_edge >= t.high
            ):
                merged[-1] = prev + gap + nxt
                continue
        merged.append(nxt)
    return merged


def _build_spans(
    runs: List[List[int]],
    sentences: List[Sentence],
    source: str,
    sent_scores: Dict[int, Tuple[float, float]],
    window_scores_by_sentence: Dict[int, List[Tuple[Window, float]]],
    t: DetectorThresholds,
    page: Optional[int],
) -> List[DetectedSpan]:
    spans: List[DetectedSpan] = []
    for run in runs:
        words = sum(sentences[i].word_count for i in run)
        if words < MIN_SPAN_WORDS:
            continue
        start = sentences[run[0]].start
        end = sentences[run[-1]].end
        if end <= start:
            continue
        text = source[start:end]
        # Word-weighted mean of constituent sentence scores.
        weighted = sum(
            sent_scores[i][0] * sentences[i].word_count for i in run
        )
        confidence = weighted / max(1, words)
        label = label_for_score(confidence, t)

        # Explainable signals: features from the windows that overlap this run.
        seen: Dict[str, Feature] = {}
        for i in run:
            for w, wscore in window_scores_by_sentence.get(i, []):
                for f in w.features:
                    if f.name not in seen:
                        seen[f.name] = f
        signals = top_features(list(seen.values()), limit=8)

        spans.append(
            DetectedSpan(
                start=start,
                end=end,
                text=text.strip(),
                confidence=confidence,
                label=label,
                signals=signals,
                sentence_indexes=run,
                word_count=words,
                page=page,
            )
        )
    return spans


def analyze_document(
    source: str,
    t: DetectorThresholds,
    window_size: int = 4,
    step: int = 2,
    page: Optional[int] = None,
) -> DocumentAnalysis:
    """Run the full pipeline on one piece of text (one PDF page or pasted
    text) and produce a DocumentAnalysis with spans + doc-level numbers."""

    warnings: List[str] = []
    sentences = segment_text(source)
    if not sentences:
        return DocumentAnalysis(
            source=source,
            sentences=[],
            analyzed_words=0,
            spans=[],
            distribution={"ai_like": 0.0, "uncertain": 0.0, "human": 0.0},
            overall_score=0.5,
            label="uncertain",
            confidence=0.0,
            insufficient_text=True,
            message="The submitted text contains no analyzable prose.",
        )

    analyzed = analyzeable_sentences(sentences)
    analyzed_words = sum(s.word_count for s in analyzed)

    windows = build_windows(
        sentences, window_size=window_size, step=step,
        min_window_words=MIN_WINDOW_WORDS,
    )
    for w in windows:
        features = _window_features(w, sentences)
        if features:
            total = sum(f.weight for f in features)
            w.score = sum(f.score * f.weight for f in features) / total
            w.score = _resolve_window_score(w.score, features)
            w.features = features

    # Sentence scores from overlapping windows.
    sent_windows: Dict[int, List[Window]] = {i: [] for i in range(len(sentences))}
    for w in windows:
        if w.score is None:
            continue
        for i in w.sentence_indexes:
            if sentences[i].kind == "text":
                sent_windows[i].append(w)

    sent_scores: Dict[int, Tuple[float, float]] = {}
    for i, ws in sent_windows.items():
        if not ws:
            continue
        scores = [w.score for w in ws]
        mean_score = sum(scores) / len(scores)
        consistency = sum(1 for s in scores if s >= t.medium) / len(scores)
        sent_scores[i] = (mean_score, consistency)

    flagged = _flag_sentences(sentences, sent_scores, t)
    runs = _runs_of_flagged(flagged, sentences)
    runs = _merge_gaps(runs, sentences, sent_scores, t)

    # Signals per sentence from its windows (for span explainability).
    window_scores_by_sentence: Dict[int, List[Tuple[Window, float]]] = {}
    for i in range(len(sentences)):
        window_scores_by_sentence[i] = []
        for w in sent_windows.get(i, []):
            if w.score is not None:
                window_scores_by_sentence[i].append((w, w.score))

    spans = _build_spans(
        runs, sentences, source, sent_scores,
        window_scores_by_sentence, t, page,
    )

    # Word-level distribution across the three bands.
    distribution = {"ai_like": 0.0, "uncertain": 0.0, "human": 0.0}
    for i, s in enumerate(sentences):
        if s.kind != "text" or i not in sent_scores:
            continue
        band = band_for_score(sent_scores[i][0], t)
        distribution[band] += s.word_count
    total_banded = sum(distribution.values())
    if total_banded > 0:
        distribution = {k: v / total_banded for k, v in distribution.items()}

    # Document score: word-weighted mean over *stable* windows.
    side = lambda sc: sc >= t.medium
    stability_by_window: Dict[int, float] = {}
    for w in windows:
        if w.score is None:
            continue
        neighbors = [
            u for u in windows
            if u.score is not None
            and set(u.sentence_indexes) & set(w.sentence_indexes)
        ]
        if not neighbors:
            stability_by_window[w.index] = 1.0
            continue
        agree = sum(
            1 for u in neighbors if side(u.score) == side(w.score)
        )
        stability_by_window[w.index] = agree / len(neighbors)

    stable = [
        w for w in windows
        if w.score is not None and stability_by_window.get(w.index, 0.0) >= 0.5
    ]
    stability_ratio = (
        len(stable) / len([w for w in windows if w.score is not None])
        if windows else 0.0
    )

    if stable:
        num = sum(w.score * w.word_count for w in stable)
        den = sum(w.word_count for w in stable)
        overall_score = num / den if den else 0.0
    else:
        overall_score = 0.5  # no agreement -> genuinely uncertain

    # Duplication safeguard: detect repeated long n-grams across prose.
    all_words: List[str] = []
    for s in analyzed:
        all_words.extend(s.words)
    duplicate_ratio = _duplicate_fraction(all_words)

    special_fraction = fraction_of_special_content(source)

    insufficient, message = short_document_advice(analyzed_words, t)
    if insufficient:
        label = "uncertain"
        overall_score = 0.5
        confidence = 0.05
    else:
        label = label_for_score(overall_score, t)
        confidence = confidence_from_reliability(
            analyzed_words,
            purity=max(0.0, 1.0 - special_fraction),
            duplicate_ratio=duplicate_ratio,
            stability_ratio=stability_ratio,
            overall_score=overall_score,
            t=t,
        )

    return DocumentAnalysis(
        source=source,
        sentences=sentences,
        analyzed_words=analyzed_words,
        spans=spans,
        distribution=distribution,
        overall_score=overall_score,
        label=label,
        confidence=confidence,
        insufficient_text=insufficient,
        message=message if insufficient else "",
        duplicate_ratio=duplicate_ratio,
        special_fraction=special_fraction,
        stability_ratio=stability_ratio,
        warnings=warnings,
    )


def _duplicate_fraction(words: List[str]) -> float:
    """Share of words inside repeated 8-grams.  Heavily duplicated documents
    (copy-paste essays) should lower confidence, not raise the AI score."""
    if len(words) < 16:
        return 0.0
    n = 8
    grams = [tuple(words[i: i + n]) for i in range(len(words) - n + 1)]
    counts = Counter(grams)
    repeated_words = 0
    for gram, count in counts.items():
        if count > 1:
            repeated_words += len(gram) * (count - 1)
    return min(1.0, repeated_words / len(words))