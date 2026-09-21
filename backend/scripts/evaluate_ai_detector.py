"""
Evaluate the multi-signal AI-text detector against a small labeled control
set and report precision / recall / F1 / false-positive rate / false-negative
rate.

This is NOT a scientifically valid benchmark: the control set is small and
written for development.  It exists to catch regressions and to calibrate
the thresholds, not to certify the detector.  Run it from the backend dir:

    python scripts/evaluate_ai_detector.py
"""

import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # noqa: E402

from app.ai.ai_detector.detector_service import analyze_text  # noqa: E402

AI_LABELS = {"potentially_ai_generated", "strong_ai_like_signals"}

HUMAN_1 = (
    "I remember driving home through the rain that night, halfway listening to the steady slap of the "
    "wipers and half replaying the argument with my brother. We had said things we didn't really mean, "
    "or maybe we did, which was worse. By the time I pulled into the driveway the last song on the radio "
    "had already faded, and I just sat there in the dark car for a few minutes, watching the water bead up "
    "on the windshield. In the morning I called him, not with an apology exactly, but with coffee, and we "
    "sat on the porch talking about the neighbors' dog instead of any of it. That was how we always made "
    "up, slowly, sideways, without ever quite landing on the actual thing. It wasn't clean and it wasn't "
    "quick, but it was ours, and somehow that mattered more."
)

HUMAN_2 = (
    "The workshop started half an hour late because the projector had been borrowed by the history "
    "department and nobody had thought to tell us until that morning. We ended up crowded around a single "
    "laptop on the desk, passing it from hand to hand like a hot potato, while Rajesh narrated what was "
    "supposed to have been a slide deck. Somewhere along the way the session turned into an argument about "
    "whether the syllabus was fair, which was familiar ground and honest ground, and I think we learned "
    "more from that than from any plan. When I finally left, the corridor lights had dimmed and the "
    "security guard was doing his rounds with a dog that wagged its tail at everyone."
)

HUMAN_3 = (
    "My grandfather kept a small notebook of plants he had never been able to identify, with sketches and "
    "Latin names scribbled out and written again. Every spring we would carry it into the hills and try to "
    "match the leaves to the drawings, which never quite worked, and that was the point. He said a name "
    "was only useful if it made you look closer, and looking closer was the whole hobby. I still have the "
    "book now, stained at the edges, and I recognize almost none of the plants, but I remember exactly "
    "which days we argued about each one and what we had for lunch afterwards."
)

AI_1 = (
    "In today's modern era, effective communication plays a crucial role in personal and professional "
    "success. Furthermore, it is important to note that clear communication fosters strong relationships "
    "and enhances collaboration across diverse teams. Moreover, in conclusion, organizations that "
    "prioritize open dialogue consistently achieve higher levels of productivity and employee satisfaction. "
    "Additionally, this highlights the importance of active listening in every interaction. It is "
    "essential that individuals develop these skills over time to remain competitive in an ever-changing "
    "landscape. Ultimately, the importance of adaptability cannot be overstated, and therefore, continuous "
    "improvement remains a fundamental pillar of growth and development."
)

AI_2 = (
    "Project management is a discipline that guarantees the successful delivery of complex objectives. "
    "Consequently, it is important to note that stakeholder engagement plays a vital role in the overall "
    "outcome of any undertaking. Furthermore, the importance of clear documentation cannot be overstated, "
    "as it ensures continuity across the entire lifecycle. Therefore, organizations should develop robust "
    "processes that emphasize adaptability and resilience. Moreover, in summary, the adoption of best "
    "practices in this field ultimately leads to improved efficiency and measurable results."
)

# Modern LLM output: natural-sounding, no heavy scaffold phrases, but with
# uniformly short-to-mid sentences and essentially no personal voice.
AI_3 = (
    "The impact of social media on mental health has become one of the defining questions of the digital age. "
    "Platforms are designed to maximize engagement, and this design has real consequences for the people who use them. "
    "Researchers have documented a consistent relationship between heavy usage and symptoms of anxiety and depression, "
    "particularly among younger users. At the same time, the same platforms provide connection for people who are "
    "otherwise isolated, which complicates any simple conclusion. The debate is not really about whether social media "
    "is good or bad, but about how individuals and societies adapt to technologies that evolve faster than our "
    "understanding of them. Regulators in several countries have begun to explore age verification and algorithmic "
    "transparency requirements as possible responses. Critics argue that such measures risk overreach and fail to "
    "address the underlying incentives that drive harmful design patterns. Proponents respond that the current "
    "approach relies almost entirely on voluntary self-regulation yet demonstrably fails to protect vulnerable "
    "populations. There is widespread agreement that education and digital literacy play an important part in any "
    "solution. Schools increasingly integrate media literacy into their curricula, teaching students to recognize "
    "manipulation and to evaluate sources critically. Yet education alone cannot address the structural features of "
    "platforms that encourage compulsive use. The most thoughtful analysis tends to avoid sweeping pronouncements and "
    "instead traces the specific mechanisms through which different features shape user behavior. Comparing the "
    "evidence across studies reveals that context matters enormously, from the age of the user to the nature of the "
    "content they consume. Ultimately, this is a policy problem as much as a personal one, and its resolution will "
    "require cooperation between researchers, industry, and governments. The stakes are significant, but so is the "
    "opportunity to build digital environments that genuinely support wellbeing."
)

HUMAN_4 = (
    "Our office shifted to a hybrid schedule in the spring and the first month was genuinely chaotic. Nobody had "
    "thought through what happened when half the team sat in the building and the other half scattered across three "
    "time zones. We would schedule a meeting at ten but someone was always on their way to pick up their kid, or the "
    "video cut out on the train. My manager kept saying we needed synchronous rituals, which drove me a little crazy, "
    "but she wasn't entirely wrong either. We ended up writing everything down, not because anyone read it, but "
    "because writing it forced someone to make a decision. The funny thing is that after a few months the chaos "
    "settled into something almost boring, and the boring version turned out to be fine. I still miss the hallway "
    "conversations, but I don't miss the commute, and I've stopped pretending that's a contradiction."
)

DATASET = [
    ("human", HUMAN_1),
    ("human", HUMAN_2),
    ("human", HUMAN_3),
    ("human", HUMAN_4),
    ("ai", AI_1),
    ("ai", AI_2),
    ("ai", AI_3),
]


def main() -> int:
    metrics = defaultdict(int)  # tp, fp, fn, tn
    print("=" * 70)
    print("AI DETECTOR EVALUATION (small labeled control set)")
    print("=" * 70)
    for true_kind, text in DATASET:
        res = analyze_text(text, result_id=f"eval-{true_kind}")
        predicted_ai = res.label in AI_LABELS and not res.insufficient_text
        true_ai = true_kind == "ai"
        key = (
            "tp" if predicted_ai and true_ai else
            "fp" if predicted_ai else
            "fn" if true_ai else
            "tn"
        )
        metrics[key] += 1
        print(
            f"  {true_kind:>6} -> {res.label:>26}  score={res.overall_score:.2f} "
            f"words={res.analyzed_words:<4} spans={len(res.detections)}  [{key}]"
        )

    tp = metrics["tp"]
    fp = metrics["fp"]
    fn = metrics["fn"]
    tn = metrics["tn"]

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0

    print("-" * 70)
    print(f"  Precision (AI examples correct) : {precision:.2f}")
    print(f"  Recall    (AI examples caught)   : {recall:.2f}")
    print(f"  F1                                : {f1:.2f}")
    print(f"  FPR (human examples flagged)      : {fpr:.2f}")
    print(f"  FNR (AI examples missed)          : {fnr:.2f}")
    print("-" * 70)
    print("  Caveat: this is a development control set, not a scientific")
    print("  benchmark. Do not use these numbers to claim real-world accuracy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())