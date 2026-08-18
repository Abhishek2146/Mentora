"""
Analytics Service
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.logger import get_logger
from app.models.quiz import QuizAttempt, Quiz
from app.models.study_plan import StudyTask, StudyPlan
from app.models.coding_problem import CodingSubmission
from app.models.progress import Progress, WeakTopic
from app.models.syllabus import Subject
from app.schemas.common import ResponseModel
from app.services.progress_service import ProgressService

logger = get_logger(__name__)

class AnalyticsService:
    def __init__(self):
        self.progress_service = ProgressService()

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
            .where(CodingSubmission.user_id == user_id, CodingSubmission.total_tests_cases > 0, CodingSubmission.passed_tests_cases == CodingSubmission.total_tests_cases)
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

        top_weak_topics = await self.progress_service.get_top_weak_topics(
            user_id=user_id, db=db, limit=5
        )

        data = {
            "total_quizzes_taken": total_quizzes,
            "avg_quiz_score": float(avg_score),
            "coding_problems_solved": coding_solved,
            "overall_progress": progress.value if progress else 0.0,
            "weak_topics_count": weak_topics_count,
            "weak_topics": [
                {"topic_name": wt.topic_name, "accuracy": wt.accuracy}
                for wt in top_weak_topics
            ],
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
                Subject.id.label("subject_id"),
                Subject.name.label("subject_name"),
                func.avg(QuizAttempt.score).label("avg_score"),
                func.count(QuizAttempt.id).label("attempts"),
            )
            .select_from(QuizAttempt)
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
            .join(Subject, Quiz.subject_id == Subject.id)
            .where(QuizAttempt.user_id == user_id)
            .group_by(Subject.id, Subject.name)
        )

        return [
            {
                "subject_id": row.subject_id,
                "subject_name": row.subject_name,
                "avg_score": float(row.avg_score),
                "attempts": row.attempts,
            }
            for row in result.fetchall()
        ]

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
