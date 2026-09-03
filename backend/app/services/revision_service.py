"""
Revision Service
"""
import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
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

        # If parsed_data is empty, try to extract topics from DB subjects/chapters,
        # then fall back to extracted_text.
        has_chapters = False
        for s in syllabus_data.get("subjects", []):
            if s.get("chapters"):
                has_chapters = True
                break

        if not has_chapters:
            logger.warning(
                "Revision plan: parsed_data empty for syllabus %d, "
                "trying DB fallback and extracted_text",
                syllabus.id,
            )
            from app.services.quiz_service import _fallback_topics_from_db
            fallback_topics = await _fallback_topics_from_db(syllabus.id, db)
            if fallback_topics:
                syllabus_data = {
                    "subjects": [{
                        "name": syllabus.title or "Course",
                        "description": "",
                        "chapters": [
                            {"name": t, "description": "", "topics": [], "estimated_hours": 0}
                            for t in fallback_topics
                        ],
                    }]
                }
            elif syllabus.extracted_text:
                # Use a summary of extracted_text as the syllabus content
                syllabus_data = {
                    "subjects": [{
                        "name": syllabus.title or "Course",
                        "description": "",
                        "chapters": [{
                            "name": "Course Content",
                            "description": "",
                            "topics": [],
                            "estimated_hours": 0,
                        }],
                    }]
                }

        # Build the text to send to the LLM
        if has_chapters:
            llm_text = (
                f"Syllabus: {syllabus.title}\n\n"
                f"{json.dumps(syllabus_data, ensure_ascii=False, indent=2)}"
            )
        elif syllabus.extracted_text:
            llm_text = (
                f"Syllabus: {syllabus.title}\n\n"
                f"Extracted syllabus content:\n"
                f"{syllabus.extracted_text[:settings.LLM_MAX_INPUT_CHARS]}"
            )
        else:
            llm_text = f"Syllabus: {syllabus.title}"

        logger.info(
            "Revision plan: syllabus_id=%d has_chapters=%s using_extracted_text=%s",
            syllabus.id, has_chapters, not has_chapters and bool(syllabus.extracted_text),
        )

        schedule_data = await self.llm_service.generate_revision_schedule(
            syllabus_data=syllabus_data,
            llm_text=llm_text,
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

            items = schedule_data.get("items", [])
            if not items:
                # Fallback: derive topics directly from the syllabus so a
                # plan is always generated, even when the LLM fails.
                from app.services.quiz_service import extract_syllabus_topics

                items = [
                    {"topic": t, "difficulty": "medium"}
                    for t in extract_syllabus_topics(syllabus_data, limit=20)
                ]

            # Spaced repetition: growing gaps of 1, 2, 3, 5, 8, ... days,
            # capped at the schedule's end date when provided.
            gap_pattern = [1, 1, 2, 3, 5, 5, 7]
            day_offset = 0
            for idx, item in enumerate(items[:30]):
                topic_name = str(item.get("topic") or item.get("title") or "").strip()
                if not topic_name:
                    continue
                day_offset += gap_pattern[min(idx, len(gap_pattern) - 1)]
                scheduled_date = start_date + timedelta(days=day_offset)
                if end_date and scheduled_date > end_date:
                    scheduled_date = end_date

                difficulty = str(item.get("difficulty") or "medium").lower()
                priority = (
                    "high" if difficulty == "hard"
                    else "low" if difficulty == "easy"
                    else "medium"
                )
                revision_item = RevisionItem(
                    schedule_id=schedule.id,
                    topic_name=topic_name[:255],
                    scheduled_date=scheduled_date,
                    revision_method="review",
                    priority=priority,
                    completed=False,
                )
                db.add(revision_item)

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
