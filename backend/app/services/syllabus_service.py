"""
Syllabus service for Mentora.

Handles syllabus-related business logic.
SQLAlchemy models are defined in app.models.syllabus.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.syllabus import Syllabus, Subject, Chapter
from app.services.llm_service import LLMService
from app.services.ocr_service import OCRService
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService
import os
logger = get_logger(__name__)


class SyllabusService:
    """
    Service class for syllabus-related operations.

    Provides methods for querying syllabus data and for
    processing uploaded syllabus files (OCR + LLM parsing).
    """

    def __init__(self):
        self.ocr_service = OCRService()
        self.llm_service = LLMService()
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService()

    # ============================================================
    # Query Methods
    # ============================================================

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

    # ============================================================
    # Processing Methods
    # ============================================================

    async def process_syllabus(self, db: AsyncSession, syllabus: Syllabus) -> dict:
        """Process uploaded syllabus file: OCR extraction + LLM parsing."""

        try:
            extracted_text = await self.ocr_service.extract_text(
                syllabus.file_path, syllabus.file_type
            )
        except Exception as e:
            logger.error(f"OCR extraction failed for syllabus {syllabus.id}: {e}")
            syllabus.status = "failed"
            await db.commit()
            return {"status": "failed", "error": str(e)}

        try:
            parsed_data = await self.llm_service.parse_syllabus_content(
                extracted_text
            )
        except Exception as e:
            logger.warning(
                f"LLM parsing failed for syllabus {syllabus.id}: {e}"
            )
            parsed_data = {}

        if parsed_data.get("subjects"):
            syllabus.parsed_data = parsed_data
            syllabus.status = "parsed"

            await self._create_subjects_chapters(db, syllabus, parsed_data)
        else:
            syllabus.status = "uploaded"
            logger.warning(
                f"Syllabus {syllabus.id} uploaded but could not be "
                "parsed by the LLM"
            )

        await db.commit()

        await self._embed_for_rag(
            syllabus,
            extracted_text,
            parsed_data,
        )

        return {"status": syllabus.status, "parsed_data": syllabus.parsed_data}
    async def _embed_for_rag(
        self, syllabus: Syllabus, extracted_text: str, parsed_data: dict
    ) -> None:
        """Chunk, embed, and store the syllabus text in Chroma."""

        if not extracted_text or not extracted_text.strip():
            logger.warning(
                f"Syllabus {syllabus.id} has no extracted text; skipping RAG embedding"
            )
            return

        base_metadata = {
            "user_id": syllabus.user_id,
            "syllabus_id": syllabus.id,
            "source": os.path.basename(syllabus.file_path)
            if syllabus.file_path
            else "unknown",
        }

        try:
            chunks = self.embedding_service.chunk_text_with_metadata(
                extracted_text, base_metadata
            )

            if not chunks:
                logger.warning(f"No chunks produced for syllabus {syllabus.id}")
                return

            collection_name = (
                self.vector_service.collection_name_for_syllabus(syllabus.id)
            )

            self.vector_service.add_documents(collection_name, chunks)
            syllabus.is_ai_processed = True

            logger.info(
                f"Embedded {len(chunks)} chunks for syllabus {syllabus.id} "
                f"into collection '{collection_name}'"
            )

        except Exception as e:
            logger.error(
                f"RAG embedding failed for syllabus {syllabus.id}: {e}"
            )
    async def _create_subjects_chapters(
        self, db: AsyncSession, syllabus: Syllabus, parsed_data: dict
    ):
        """Create and persist subjects and chapters from parsed data."""

        subjects_data = parsed_data.get("subjects", [])

        for order, subj_data in enumerate(subjects_data):
            subject = Subject(
                syllabus_id=syllabus.id,
                name=subj_data.get("name", f"Subject {order + 1}"),
                description=subj_data.get("description"),
                subject_order=order,
            )
            db.add(subject)
            await db.flush()

            for chapter_order, chapter_data in enumerate(
                subj_data.get("chapters", [])
            ):
                chapter = Chapter(
                    subject_id=subject.id,
                    name=chapter_data.get("name", f"Chapter {chapter_order + 1}"),
                    description=chapter_data.get("description"),
                    chapter_order=chapter_order,
                    topics=chapter_data.get("topics"),
                )
                db.add(chapter)

        logger.info(f"Created subjects/chapters for syllabus {syllabus.id}")
