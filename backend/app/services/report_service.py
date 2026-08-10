"""
Report Service - generates weekly and analytical reports
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.logger import get_logger
from app.models.chat_history import WeeklyReport
from app.models.quiz import QuizAttempt
from app.models.coding_problem import CodingSubmission
from app.models.study_plan import StudyTask, StudyPlan
from app.models.flashcard import Flashcard

logger = get_logger(__name__)


class ReportService:
    async def generate_weekly_report(self, user_id: int, db: AsyncSession) -> dict:
        """Generate a weekly report for the user."""
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        quiz_result = await db.execute(
            select(
                func.count(QuizAttempt.id).label("quizzes_taken"),
                func.sum(func.case((QuizAttempt.is_passed == True, 1), else_=0)).label("quizzes_passed"),
                func.avg(QuizAttempt.score).label("avg_score"),
                func.sum(QuizAttempt.time_taken).label("quiz_time"),
            ).where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.created_at >= week_start,
                QuizAttempt.created_at <= week_end,
            )
        )
        quiz_stats = quiz_result.fetchone()

        coding_result = await db.execute(
            select(func.count(CodingSubmission.id).label("problems_solved"))
            .where(
                CodingSubmission.user_id == user_id,
                CodingSubmission.created_at >= week_start,
                CodingSubmission.created_at <= week_end,
            )
        )
        coding_stats = coding_result.fetchone()

        tasks_result = await db.execute(
            select(func.count(StudyTask.id).label("tasks_completed"))
            .join(StudyPlan)
            .where(
                StudyPlan.user_id == user_id,
                StudyTask.completed == True,
                StudyTask.updated_at >= week_start,
                StudyTask.updated_at <= week_end,
            )
        )
        task_stats = tasks_result.fetchone()

        report = WeeklyReport(
            user_id=user_id,
            week_start=week_start.strftime("%Y-%m-%d"),
            week_end=week_end.strftime("%Y-%m-%d"),
            study_time_minutes=quiz_stats.quiz_time or 0 if quiz_stats else 0,
            quizzes_taken=quiz_stats.quizzes_taken or 0 if quiz_stats else 0,
            quizzes_passed=quiz_stats.quizzes_passed or 0 if quiz_stats else 0,
            flashcards_reviewed=0,
            coding_problems_solved=coding_stats.problems_solved or 0 if coding_stats else 0,
            report_data=f"Weekly report for {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}. Avg quiz score: {quiz_stats.avg_score or 0:.1f}%",
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        return {
            "report": report,
            "summary": {
                "quizzes_taken": quiz_stats.quizzes_taken or 0,
                "quizzes_passed": quiz_stats.quizzes_passed or 0,
                "avg_score": float(quiz_stats.avg_score) if quiz_stats and quiz_stats.avg_score else 0.0,
                "coding_solved": coding_stats.problems_solved or 0,
                "tasks_completed": task_stats.tasks_completed or 0,
            },
        }

    async def get_reports(self, user_id: int, limit: int, db: AsyncSession) -> list:
        result = await db.execute(
            select(WeeklyReport)
            .where(WeeklyReport.user_id == user_id)
            .order_by(WeeklyReport.week_start.desc())
            .limit(limit)
        )
        return result.scalars().all()
