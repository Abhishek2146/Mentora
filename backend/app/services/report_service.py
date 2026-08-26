"""
Revision & Report Services
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.logger import get_logger
from app.models.revision import RevisionSchedule, RevisionItem
from app.models.syllabus import Syllabus
from app.models.chat_history import WeeklyReport, ChatSession, ChatMessage
from app.services.llm_service import LLMService
from app.services.progress_service import ProgressService

logger = get_logger(__name__)


class RevisionService:
    def __init__(self):
        self.llm_service = LLMService()
        self.progress_service = ProgressService()

    async def generate_revision_schedule(
        self,
        user_id: int,
        syllabus_id: int,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        db: AsyncSession = None,
    ) -> dict:
        """Generate a spaced repetition revision schedule."""
        syllabus_result = await db.execute(
            select(Syllabus).where(Syllabus.id == syllabus_id, Syllabus.user_id == user_id)
        )
        syllabus = syllabus_result.scalars().first()
        if not syllabus:
            raise ValueError("Syllabus not found")

        syllabus_data = syllabus.parsed_data or {"subjects": []}

        schedule_data = await self.llm_service.generate_revision_schedule(
            syllabus_data=syllabus_data,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat() if end_date else None,
        )

        # Pull the student's weak topics (reusing the same helper the AI
        # Tutor uses for personalization) so revision prioritizes topics
        # they've actually struggled with, not just a generic spaced
        # repetition pass over the whole syllabus.
        weak_topics = await self.progress_service.get_top_weak_topics(
            user_id=user_id, db=db, syllabus_id=syllabus_id, limit=5
        )
        weak_topic_accuracy = {
            wt.topic_name.strip().lower(): wt.accuracy for wt in weak_topics
        }

        schedule = RevisionSchedule(
            user_id=user_id,
            syllabus_id=syllabus_id,
            title=f"Revision Plan - {start_date.strftime('%Y-%m-%d')}",
            start_date=start_date,
            end_date=end_date,
        )

        if db:
            db.add(schedule)
            await db.commit()
            await db.refresh(schedule)

            interval = 1
            topics = schedule_data.get("items", [])
            covered = set()

            for item in topics[:20]:
                topic_name = item.get("topic", "")
                key = topic_name.strip().lower()
                is_weak = key in weak_topic_accuracy

                # Weak topics get scheduled immediately (day 1) instead of
                # waiting their turn in the generic spaced-repetition order.
                scheduled_date = start_date + timedelta(days=1 if is_weak else interval)

                revision_item = RevisionItem(
                    schedule_id=schedule.id,
                    topic_name=topic_name,
                    scheduled_date=scheduled_date,
                    completed=False,
                    priority="high" if is_weak else "medium",
                    is_ai_recommended=is_weak,
                    recommendation=(
                        f"Prioritized: you scored {weak_topic_accuracy[key]:.0f}% "
                        "on quizzes for this topic."
                        if is_weak
                        else None
                    ),
                )
                db.add(revision_item)
                covered.add(key)
                interval += 1 if interval < 7 else 0

            # If a weak topic wasn't picked up by the LLM-generated
            # schedule at all (e.g. it grouped/renamed topics), still add
            # it explicitly so it isn't silently dropped from revision.
            for wt in weak_topics:
                key = wt.topic_name.strip().lower()
                if key in covered:
                    continue
                db.add(
                    RevisionItem(
                        schedule_id=schedule.id,
                        topic_name=wt.topic_name,
                        scheduled_date=start_date + timedelta(days=1),
                        completed=False,
                        priority="high",
                        is_ai_recommended=True,
                        recommendation=(
                            f"Prioritized: you scored {wt.accuracy:.0f}% "
                            "on quizzes for this topic."
                        ),
                    )
                )
                covered.add(key)

            await db.commit()

        return {"schedule": schedule, "schedule_data": schedule_data}


    async def get_due_items(self, user_id: int, db: AsyncSession) -> list:
        """Get revision items that are due today."""
        today = datetime.utcnow().date()
        result = await db.execute(
            select(RevisionItem)
            .join(RevisionSchedule)
            .where(
                RevisionSchedule.user_id == user_id,
                RevisionItem.completed == False,
                RevisionItem.scheduled_date <= today,
            )
        )
        return result.scalars().all()


class ReportService:
    def __init__(self):
        self.llm_service = LLMService()

    async def generate_weekly_report(self, user_id: int, db: AsyncSession) -> dict:
        """Generate a weekly study report for the user."""
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Get study sessions from this week
        sessions_result = await db.execute(
            select(ChatSession)
            .join(ChatMessage)
            .where(
                ChatSession.user_id == user_id,
                ChatMessage.created_at >= datetime.combine(week_start, datetime.min.time()),
                ChatMessage.created_at <= datetime.combine(week_end, datetime.max.time()),
            )
            .distinct()
        )
        sessions = sessions_result.scalars().all()

        # Count messages as proxy for study time
        messages_result = await db.execute(
            select(func.count(ChatMessage.id))
            .join(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatMessage.created_at >= datetime.combine(week_start, datetime.min.time()),
                ChatMessage.created_at <= datetime.combine(week_end, datetime.max.time()),
            )
        )
        message_count = messages_result.scalar() or 0
        study_time_minutes = message_count * 2  # Rough estimate

        # Get topics studied from chat sessions
        topics = []
        for session in sessions:
            if session.title:
                topics.append(session.title)

        # Create the report
        report = WeeklyReport(
            user_id=user_id,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            study_time_minutes=study_time_minutes,
            topics_studied=",".join(topics[:10]) if topics else None,
            quizzes_taken=0,
            quizzes_passed=0,
            flashcards_reviewed=0,
            coding_problems_solved=0,
            report_data=None,
        )

        db.add(report)
        await db.commit()
        await db.refresh(report)

        return {
            "id": report.id,
            "week_start": report.week_start,
            "week_end": report.week_end,
            "study_time_minutes": report.study_time_minutes,
            "topics_studied": topics[:10],
        }