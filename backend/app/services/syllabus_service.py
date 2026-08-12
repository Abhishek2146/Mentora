
"""
Syllabus service for Mentora.

Handles syllabus-related business logic.
SQLAlchemy models are defined in app.models.syllabus.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.syllabus import Syllabus, Subject, Chapter


class SyllabusService:
    """
    Service class for syllabus-related operations.
    """

    async def get_syllabus(
        self,
        db: AsyncSession,
        syllabus_id: int,
    ):
        """Get a syllabus by ID."""

        result = await db.execute(
            select(Syllabus).where(
                Syllabus.id == syllabus_id
            )
        )

        return result.scalars().first()

    async def get_syllabus_subjects(
        self,
        db: AsyncSession,
        syllabus_id: int,
    ):
        """Get all subjects belonging to a syllabus."""

        result = await db.execute(
            select(Subject)
            .where(Subject.syllabus_id == syllabus_id)
            .order_by(Subject.subject_order)
        )

        return result.scalars().all()

    async def get_subject_chapters(
        self,
        db: AsyncSession,
        subject_id: int,
    ):
        """Get all chapters belonging to a subject."""

        result = await db.execute(
            select(Chapter)
            .where(Chapter.subject_id == subject_id)
            .order_by(Chapter.chapter_order)
        )

        return result.scalars().all()
