"""
Analytics Service
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.logger import get_logger
from app.models.quiz import QuizAttempt
from app.models.study_plan import StudyTask, StudyPlan
from app.models.coding_problem import CodingSubmission
from app.models.progress import Progress, WeakTopic
from app.models.flashcard import FlashcardDeck, Flashcard
from app.models.syllabus import Syllabus, Subject, Chapter
from app.schemas.common import ResponseModel

logger = get_logger(__name__)

# A topic is considered "mastered" once its tracked accuracy reaches this value.
MASTERY_THRESHOLD = 75.0


class AnalyticsService:
    async def get_dashboard_stats(self, user_id: int, db: AsyncSession) -> dict:
        """Compute real stats for the frontend dashboard cards (with weekly deltas)."""
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        prev_week_start = now - timedelta(days=14)

        # ---- Study hours (quiz time spent, in hours) ----
        def _hours(seconds) -> float:
            return round((seconds or 0) / 3600.0, 1)

        total_time_result = await db.execute(
            select(func.sum(QuizAttempt.time_taken)).where(QuizAttempt.user_id == user_id)
        )
        study_hours_total = _hours(total_time_result.scalar())

        week_time_result = await db.execute(
            select(func.sum(QuizAttempt.time_taken)).where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.created_at >= week_start,
            )
        )
        study_hours_week = _hours(week_time_result.scalar())

        # ---- Quiz average (all-time + this week's delta vs previous week) ----
        avg_score_result = await db.execute(
            select(func.avg(QuizAttempt.score)).where(QuizAttempt.user_id == user_id)
        )
        quiz_avg = round(float(avg_score_result.scalar() or 0.0), 1)

        this_week_avg_result = await db.execute(
            select(func.avg(QuizAttempt.score)).where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.created_at >= week_start,
            )
        )
        prev_week_avg_result = await db.execute(
            select(func.avg(QuizAttempt.score)).where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.created_at >= prev_week_start,
                QuizAttempt.created_at < week_start,
            )
        )
        this_week_avg = this_week_avg_result.scalar()
        prev_week_avg = prev_week_avg_result.scalar()
        if this_week_avg is not None and prev_week_avg is not None:
            quiz_avg_change = round(float(this_week_avg) - float(prev_week_avg), 1)
        else:
            quiz_avg_change = None

        # ---- Flashcards reviewed ----
        flashcard_count_query = (
            select(func.count(Flashcard.id))
            .select_from(Flashcard)
            .join(FlashcardDeck, Flashcard.deck_id == FlashcardDeck.id)
            .where(
                FlashcardDeck.user_id == user_id,
                Flashcard.last_reviewed.isnot(None),
            )
        )
        flashcards_done_result = await db.execute(flashcard_count_query)
        flashcards_done = flashcards_done_result.scalar() or 0

        flashcards_week_result = await db.execute(
            flashcard_count_query.where(Flashcard.last_reviewed >= week_start.isoformat())
        )
        flashcards_week = flashcards_week_result.scalar() or 0

        # ---- Topics mastered / total ----
        chapter_result = await db.execute(
            select(Chapter.topics)
            .join(Subject, Chapter.subject_id == Subject.id)
            .join(Syllabus, Subject.syllabus_id == Syllabus.id)
            .where(Syllabus.user_id == user_id)
        )
        topics_total = sum(len(t or []) for t in chapter_result.scalars().all())

        mastered_result = await db.execute(
            select(func.count(func.distinct(func.lower(WeakTopic.topic_name)))).where(
                WeakTopic.user_id == user_id,
                WeakTopic.accuracy >= MASTERY_THRESHOLD,
            )
        )
        topics_mastered = mastered_result.scalar() or 0

        newly_mastered_result = await db.execute(
            select(func.count(func.distinct(func.lower(WeakTopic.topic_name)))).where(
                WeakTopic.user_id == user_id,
                WeakTopic.accuracy >= MASTERY_THRESHOLD,
                WeakTopic.last_attempted >= week_start.date(),
            )
        )
        topics_mastered_week = newly_mastered_result.scalar() or 0

        # ---- Tasks due today ----
        today = now.date()
        tasks_today_result = await db.execute(
            select(func.count(StudyTask.id))
            .select_from(StudyTask)
            .join(StudyPlan, StudyTask.study_plan_id == StudyPlan.id)
            .where(
                StudyPlan.user_id == user_id,
                StudyTask.completed == False,
                func.date(StudyTask.due_date) == today,
            )
        )
        tasks_due_today = tasks_today_result.scalar() or 0

        return {
            "study_hours": {
                "total": study_hours_total,
                "week_change": study_hours_week,
            },
            "quiz_average": {
                "value": quiz_avg,
                "week_change": quiz_avg_change,
            },
            "flashcards_done": {
                "total": flashcards_done,
                "week_change": flashcards_week,
            },
            "topics_mastered": {
                "mastered": topics_mastered,
                "total": topics_total,
                "week_change": topics_mastered_week,
            },
            "tasks_due_today": tasks_due_today,
        }


    async def get_dashboard_analytics(self, user_id: int, db: AsyncSession) -> ResponseModel:
        """Get dashboard analytics summary."""
        total_attempts_result = await db.execute(
            select(func.count(QuizAttempt.id)).where(QuizAttempt.user_id == user_id)
        )
        total_quizzes = total_attempts_result.scalar() or 0

        avg_score_result = await db.execute(
            select(func.avg(QuizAttempt.score)).where(QuizAttempt.user_id == user_id)
        )
        avg_score = avg_score_result.scalar() or 0.0

        coding_result = await db.execute(
            select(func.count(CodingSubmission.id))
            .where(CodingSubmission.user_id == user_id, CodingSubmission.status == "passed")
        )
        coding_solved = coding_result.scalar() or 0

        progress_result = await db.execute(
            select(Progress).where(Progress.user_id == user_id, Progress.progress_type == "overall")
        )
        progress = progress_result.scalars().first()

        weak_topics_result = await db.execute(
            select(func.count(WeakTopic.id)).where(WeakTopic.user_id == user_id)
        )
        weak_topics_count = weak_topics_result.scalar() or 0

        data = {
            "total_quizzes_taken": total_quizzes,
            "avg_quiz_score": float(avg_score),
            "coding_problems_solved": coding_solved,
            "overall_progress": progress.value if progress else 0.0,
            "weak_topics_count": weak_topics_count,
        }

        return ResponseModel(success=True, data=data, message="Dashboard analytics retrieved")

    async def get_study_time_trend(self, user_id: int, days: int, db: AsyncSession) -> List[dict]:
        """Get study time trend over the last N days."""
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(
                func.date(QuizAttempt.created_at).label("date"),
                func.sum(QuizAttempt.time_taken).label("study_time"),
            )
            .where(QuizAttempt.user_id == user_id, QuizAttempt.created_at >= start_date)
            .group_by(func.date(QuizAttempt.created_at))
            .order_by("date")
        )

        return [{"date": row.date, "study_time": row.study_time} for row in result.fetchall()]

    async def get_quiz_performance(self, user_id: int, db: AsyncSession) -> List[dict]:
        """Get quiz performance over time."""
        result = await db.execute(
            select(
                func.date(QuizAttempt.created_at).label("date"),
                func.avg(QuizAttempt.score).label("avg_score"),
                func.count(QuizAttempt.id).label("attempts"),
            )
            .where(QuizAttempt.user_id == user_id)
            .group_by(func.date(QuizAttempt.created_at))
            .order_by("date")
        )

        return [{"date": row.date, "avg_score": float(row.avg_score), "attempts": row.attempts} for row in result.fetchall()]

    async def get_subject_breakdown(self, user_id: int, db: AsyncSession) -> List[dict]:
        """Get performance breakdown by subject."""
        result = await db.execute(
            select(
                QuizAttempt.quiz_id,
                func.avg(QuizAttempt.score).label("avg_score"),
                func.count(QuizAttempt.id).label("attempts"),
            )
            .where(QuizAttempt.user_id == user_id)
            .group_by(QuizAttempt.quiz_id)
        )

        return [{"quiz_id": row.quiz_id, "avg_score": float(row.avg_score), "attempts": row.attempts} for row in result.fetchall()]

    async def get_activity_log(self, user_id: int, limit: int, db: AsyncSession) -> List[dict]:
        """Get user activity log."""
        activities = []

        quiz_result = await db.execute(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.created_at.desc())
            .limit(limit // 3)
        )
        for attempt in quiz_result.scalars().all():
            activities.append({
                "type": "quiz_attempt",
                "description": f"Quiz attempt: {attempt.score}% score",
                "timestamp": attempt.created_at.isoformat() if attempt.created_at else None,
            })

        coding_result = await db.execute(
            select(CodingSubmission)
            .where(CodingSubmission.user_id == user_id)
            .order_by(CodingSubmission.created_at.desc())
            .limit(limit // 3)
        )
        for sub in coding_result.scalars().all():
            activities.append({
                "type": "coding_submission",
                "description": f"Code submission: {'passed' if sub.status == 'passed' else 'failed'}",
                "timestamp": sub.created_at.isoformat() if sub.created_at else None,
            })

        task_result = await db.execute(
            select(StudyTask)
            .join(StudyPlan)
            .where(StudyPlan.user_id == user_id)
            .order_by(StudyTask.created_at.desc())
            .limit(limit // 3)
        )
        for task in task_result.scalars().all():
            activities.append({
                "type": "study_task",
                "description": f"Task: {task.title} - {'completed' if task.completed else 'pending'}",
                "timestamp": task.created_at.isoformat() if task.created_at else None,
            })

        return sorted(activities, key=lambda x: x.get("timestamp") or "", reverse=True)[:limit]
