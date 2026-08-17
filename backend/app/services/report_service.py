"""
Report Service - generates weekly and analytical reports.
"""
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.core.logger import get_logger
from app.models.chat_history import WeeklyReport
from app.models.quiz import QuizAttempt
from app.models.coding_problem import CodingSubmission
from app.models.study_plan import StudyTask, StudyPlan
from app.models.flashcard import Flashcard

logger = get_logger(__name__)


class ReportService:
    async def generate_weekly_report(self, user_id: int, db: AsyncSession) -> dict:
        now = datetime.utcnow()
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_end = week_start + timedelta(days=7)

        quiz_result = await db.execute(
            select(
                func.count(QuizAttempt.id).label("quizzes_taken"),
                func.sum(case((QuizAttempt.is_passed.is_(True), 1), else_=0)).label("quizzes_passed"),
                func.avg(QuizAttempt.score).label("avg_score"),
                func.coalesce(func.sum(QuizAttempt.time_taken), 0).label("quiz_time"),
            ).where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.created_at >= week_start,
                QuizAttempt.created_at < week_end,
            )
        )
        quiz_stats = quiz_result.one()

        coding_result = await db.execute(
            select(func.count(CodingSubmission.id).label("problems_solved")).where(
                CodingSubmission.user_id == user_id,
                CodingSubmission.created_at >= week_start,
                CodingSubmission.created_at < week_end,
                CodingSubmission.status == "passed",
            )
        )
        coding_stats = coding_result.one()

        tasks_result = await db.execute(
            select(func.count(StudyTask.id).label("tasks_completed"))
            .join(StudyPlan, StudyTask.study_plan_id == StudyPlan.id)
            .where(
                StudyPlan.user_id == user_id,
                StudyTask.completed.is_(True),
                StudyTask.updated_at >= week_start,
                StudyTask.updated_at < week_end,
            )
        )
        task_stats = tasks_result.one()

        # Flashcards belong to users through their deck.
        from app.models.flashcard import FlashcardDeck
        flashcard_result = await db.execute(
            select(func.count(Flashcard.id))
            .join(FlashcardDeck, Flashcard.deck_id == FlashcardDeck.id)
            .where(
                FlashcardDeck.user_id == user_id,
                Flashcard.last_reviewed.is_not(None),
                Flashcard.last_reviewed >= week_start.isoformat(),
                Flashcard.last_reviewed < week_end.isoformat(),
            )
        )
        flashcards_reviewed = flashcard_result.scalar_one()

        avg_score = float(quiz_stats.avg_score or 0.0)
        report = WeeklyReport(
            user_id=user_id,
            week_start=week_start.strftime("%Y-%m-%d"),
            week_end=(week_end - timedelta(days=1)).strftime("%Y-%m-%d"),
            study_time_minutes=int(quiz_stats.quiz_time or 0) // 60,
            quizzes_taken=int(quiz_stats.quizzes_taken or 0),
            quizzes_passed=int(quiz_stats.quizzes_passed or 0),
            flashcards_reviewed=flashcards_reviewed,
            coding_problems_solved=int(coding_stats.problems_solved or 0),
            report_data=(
                f"Weekly report for {week_start:%Y-%m-%d} to "
                f"{week_end - timedelta(days=1):%Y-%m-%d}. "
                f"Average quiz score: {avg_score:.1f}%."
            ),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        return {
            "report": report,
            "summary": {
                "quizzes_taken": int(quiz_stats.quizzes_taken or 0),
                "quizzes_passed": int(quiz_stats.quizzes_passed or 0),
                "avg_score": avg_score,
                "coding_solved": int(coding_stats.problems_solved or 0),
                "tasks_completed": int(task_stats.tasks_completed or 0),
                "flashcards_reviewed": flashcards_reviewed,
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
