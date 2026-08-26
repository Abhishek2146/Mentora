"""
Progress Service
"""
from collections import defaultdict
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.logger import get_logger
from app.models.progress import Progress, WeakTopic
from app.models.syllabus import Syllabus
from app.models.quiz import QuizAttempt, Quiz, Question
from app.models.flashcard import FlashcardDeck, Flashcard

logger = get_logger(__name__)

# Buckets used when a question/card cannot be matched to a syllabus topic.
GENERAL_TOPIC = "General"

# Flashcard scheduling model constants (mirrors FlashcardService):
# ease_factor starts at 250 and drops toward ~130 for poorly-known cards.
FC_EASE_DEFAULT = 250
FC_EASE_MIN = 130


def _flatten_syllabus_topics(parsed_data: Optional[dict], limit: int = 200) -> List[str]:
    """Flatten parsed syllabus into chapter/topic names."""
    topics: List[str] = []
    if not isinstance(parsed_data, dict):
        return topics
    for subject in (parsed_data.get("subjects") or []):
        if not isinstance(subject, dict):
            continue
        subject_name = subject.get("name")
        if subject_name:
            topics.append(str(subject_name))
        for chapter in (subject.get("chapters") or []):
            if not isinstance(chapter, dict):
                continue
            name = chapter.get("name")
            if name:
                topics.append(str(name))
            for t in (chapter.get("topics") or [])[:20]:
                if t:
                    topics.append(str(t))
    return topics[:limit]


def _match_topic(text: str, topics: List[str]) -> str:
    """Best-effort match of a question/card text to a syllabus topic."""
    haystack = (text or "").lower()
    if not haystack:
        return GENERAL_TOPIC
    best: str = ""
    best_len = 0
    for topic in topics:
        needle = topic.strip().lower()
        if len(needle) >= 4 and needle in haystack and len(needle) > best_len:
            best = topic
            best_len = len(needle)
    return best or GENERAL_TOPIC


def _deck_topic(deck_title: str, topics: List[str]) -> str:
    """Derive a topic from a flashcard deck title (e.g. 'AI Generated - X')."""
    title = deck_title or ""
    for prefix in ("AI Generated - ", "AI Generated-", "Generated - "):
        if title.startswith(prefix):
            title = title[len(prefix):]
            break
    title = title.strip()
    if not title:
        return GENERAL_TOPIC
    lowered = title.lower()
    for topic in topics:
        if topic.strip().lower() in lowered or lowered in topic.strip().lower():
            return topic
    return title.split(" - ")[0][:255]


def _flashcard_mastery(card: Flashcard) -> float:
    """Estimate 0-100 mastery of a single flashcard from SRS stats."""
    reps = card.repetitions or 0
    if reps <= 0:
        return 0.0
    ease = card.ease_factor or FC_EASE_DEFAULT
    # Map ease range [FC_EASE_MIN, 320] onto [0, 100].
    ratio = (ease - FC_EASE_MIN) / (320 - FC_EASE_MIN)
    mastery = max(0.0, min(1.0, ratio)) * 100
    # Cards seen more times are measured with more confidence.
    return min(100.0, mastery)


class ProgressService:
    def __init__(self):
        pass

    async def get_top_weak_topics(
        self,
        user_id: int,
        db: AsyncSession,
        syllabus_id: Optional[int] = None,
        limit: int = 3,
    ) -> List[WeakTopic]:
        """Return the user's weakest topics (lowest accuracy first), used
        by the AI Tutor / Voice Tutor to personalize explanations.
        """
        query = select(WeakTopic).where(WeakTopic.user_id == user_id)
        if syllabus_id:
            query = query.where(WeakTopic.syllabus_id == syllabus_id)
        query = query.order_by(WeakTopic.accuracy.asc()).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def update_progress(self, user_id: int, progress_type: str, value: float, db: AsyncSession):
        """Update or create a progress entry."""
        result = await db.execute(
            select(Progress).where(
                Progress.user_id == user_id, Progress.progress_type == progress_type
            )
        )
        progress = result.scalars().first()

        if progress:
            progress.value = value
            db.add(progress)
        else:
            progress = Progress(
                user_id=user_id, progress_type=progress_type, value=value
            )
            db.add(progress)

        await db.commit()
        return progress

    async def compute_topic_stats(self, user_id: int, db: AsyncSession) -> Dict[str, Dict[str, Any]]:
        """Aggregate performance per topic across every practice source:
        quizzes, generated MCQs, mock exams (all stored as QuizAttempts)
        and flashcard reviews.
        """
        topics: List[str] = []
        syllabus_result = await db.execute(
            select(Syllabus)
            .where(Syllabus.user_id == user_id)
            .order_by(Syllabus.id.desc())
            .limit(1)
        )
        syllabus = syllabus_result.scalars().first()
        if syllabus:
            topics = _flatten_syllabus_topics(syllabus.parsed_data)

        stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "correct": 0,
            "attempts": 0,
            "syllabus_id": None,
            "quizzes": 0,
            "exams": 0,
            "mcqs": 0,
            "flashcards": 0,
        })

        # ---- Quizzes / MCQs / Mock exams (all persisted as QuizAttempt) ----
        attempts_result = await db.execute(
            select(QuizAttempt).options(selectinload(QuizAttempt.quiz)).where(
                QuizAttempt.user_id == user_id
            ).order_by(QuizAttempt.created_at.asc())
        )
        attempts = attempts_result.scalars().all()

        quiz_ids = {a.quiz_id for a in attempts}
        questions_by_quiz: Dict[int, List[Question]] = defaultdict(list)
        if quiz_ids:
            questions_result = await db.execute(
                select(Question).where(Question.quiz_id.in_(quiz_ids))
            )
            for q in questions_result.scalars().all():
                questions_by_quiz[q.quiz_id].append(q)

        for attempt in attempts:
            quiz = attempt.quiz
            is_exam = bool(quiz and (quiz.title or "").startswith("Mock Exam"))
            questions = questions_by_quiz.get(attempt.quiz_id, [])
            answers = attempt.answers if isinstance(attempt.answers, dict) else {}

            for question in questions:
                selected = answers.get(str(question.id))
                is_correct = (
                    selected is not None
                    and str(selected).strip().lower()
                    == str(question.correct_answer).strip().lower()
                )
                topic = _match_topic(question.question_text or "", topics)
                s = stats[topic]
                s["attempts"] += 1
                if is_correct:
                    s["correct"] += 1
                if is_exam:
                    s["exams"] += 1
                elif quiz and quiz.is_ai_generated:
                    s["mcqs"] += 1
                else:
                    s["quizzes"] += 1

        # ---- Flashcards ----
        decks_result = await db.execute(
            select(FlashcardDeck).options(selectinload(FlashcardDeck.flashcards)).where(
                FlashcardDeck.user_id == user_id
            )
        )
        for deck in decks_result.scalars().all():
            topic = _deck_topic(deck.title or "", topics)
            reviewed = [
                c for c in (deck.flashcards or []) if (c.repetitions or 0) > 0
            ]
            if not reviewed:
                continue
            s = stats[topic]
            for card in reviewed:
                mastery = _flashcard_mastery(card)
                # A review counts as one attempt; mastery decides how much
                # of it counts as correct.
                s["attempts"] += 1
                s["correct"] += mastery / 100.0
                s["flashcards"] += 1

        if syllabus:
            for s in stats.values():
                s["syllabus_id"] = syllabus.id

        return dict(stats)

    async def detect_weak_topics(
        self,
        user_id: int,
        syllabus_id: Optional[int],
        db: AsyncSession,
    ) -> List[WeakTopic]:
        """Detect weak topics from quiz/MCQ/exam attempts AND flashcard
        review performance (deterministic, no LLM required).
        """
        stats = await self.compute_topic_stats(user_id, db)

        if not stats:
            # Nothing attempted yet - keep any previously detected rows.
            existing = await db.execute(select(WeakTopic).where(WeakTopic.user_id == user_id))
            return list(existing.scalars().all())

        weak_topics: List[WeakTopic] = []
        for topic_name, s in stats.items():
            attempts = s["attempts"]
            if attempts <= 0:
                continue
            accuracy = (s["correct"] / attempts) * 100 if attempts else 0.0
            # Confidence grows with sample size, capped at 100%.
            confidence = min(100.0, attempts * 12.0)

            if accuracy < 50:
                action = (
                    f"High priority: revisit '{topic_name}' with the AI tutor, "
                    "then practice MCQs to reinforce it."
                )
            elif accuracy < 75:
                action = (
                    f"Medium priority: review '{topic_name}' flashcards "
                    "and take a short quiz to check your understanding."
                )
            else:
                action = f"Doing well on '{topic_name}' - keep it in your revision rotation."

            weak_topics.append(
                WeakTopic(
                    user_id=user_id,
                    syllabus_id=syllabus_id or s.get("syllabus_id"),
                    topic_name=topic_name,
                    accuracy=round(accuracy, 2),
                    confidence_level=round(confidence, 2),
                    total_attempts=attempts,
                    last_attempted=datetime.utcnow().date(),
                    recommended_action=action,
                )
            )

        weak_topics.sort(key=lambda wt: wt.accuracy)

        # Replace previous detections so the list stays fresh and duplicate-free.
        existing_result = await db.execute(select(WeakTopic).where(WeakTopic.user_id == user_id))
        for old in existing_result.scalars().all():
            await db.delete(old)
        await db.flush()

        for wt in weak_topics[:25]:
            db.add(wt)
        await db.commit()
        return weak_topics[:25]

    async def get_progress_overview(self, user_id: int, db: AsyncSession) -> dict:
        """Overall progress across all sources, including improvement over time."""
        stats = await self.compute_topic_stats(user_id, db)

        total_attempts = sum(s["attempts"] for s in stats.values())
        total_correct = sum(s["correct"] for s in stats.values())
        overall = (total_correct / total_attempts) * 100 if total_attempts else 0.0

        source_totals = {
            "quizzes": sum(s["quizzes"] for s in stats.values()),
            "exams": sum(s["exams"] for s in stats.values()),
            "mcqs": sum(s["mcqs"] for s in stats.values()),
            "flashcards": sum(s["flashcards"] for s in stats.values()),
        }

        # Improvement trend: compare average score of the most recent quiz/
        # exam attempts against earlier ones.
        attempts_result = await db.execute(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.created_at.asc())
        )
        scores = [a.score for a in attempts_result.scalars().all() if a.total_questions]
        improvement = None
        if len(scores) >= 4:
            half = len(scores) // 2
            older = sum(scores[:half]) / half
            recent = sum(scores[half:]) / (len(scores) - half)
            improvement = round(recent - older, 1)

        topics = sorted(
            (
                {
                    "topic_name": name,
                    "accuracy": round((s["correct"] / s["attempts"]) * 100, 2) if s["attempts"] else 0.0,
                    "attempts": s["attempts"],
                }
                for name, s in stats.items()
                if s["attempts"] > 0
            ),
            key=lambda t: t["accuracy"],
        )

        return {
            "overall_mastery": round(overall, 1),
            "improvement": improvement,
            "total_attempts": total_attempts,
            "sources": source_totals,
            "topics": topics,
        }

    async def get_progress_summary(self, user_id: int, db: AsyncSession) -> dict:
        """Get progress summary."""
        result = await db.execute(
            select(Progress).where(Progress.user_id == user_id)
        )
        progress_entries = result.scalars().all()

        return {
            "progress": [
                {
                    "type": p.progress_type,
                    "value": p.value,
                    "target": p.target_value,
                }
                for p in progress_entries
            ]
        }
