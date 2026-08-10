"""
Revision Service
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logger import get_logger
from app.models.revision import RevisionSchedule, RevisionItem
from app.models.syllabus import Syllabus
from app.services.llm_service import LLMService

logger = get_logger(__name__)


class RevisionService:
    def __init__(self):
        self.llm_service = LLMService()

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
            for item in topics[:20]:
                scheduled_date = start_date + timedelta(days=interval)
                revision_item = RevisionItem(
                    schedule_id=schedule.id,
                    topic_name=item.get("topic", ""),
                    scheduled_date=scheduled_date,
                    completed=False,
                )
                db.add(revision_item)
                interval += 1 if interval < 7 else 0

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
