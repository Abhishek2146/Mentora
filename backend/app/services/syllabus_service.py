"""
Syllabus processing service
"""
import os
import tempfile
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logger import get_logger
from app.models.syllabus import Syllabus, Subject, Chapter
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService

logger = get_logger(__name__)


class SyllabusService:
    def __init__(self):
        self.ocr_service = OCRService()
        self.llm_service = LLMService()

    async def process_syllabus(self, db: AsyncSession, syllabus: Syllabus) -> dict:
        """Process uploaded syllabus file: OCR extraction + LLM parsing."""
        try:
            extracted_text = await self.ocr_service.extract_text(
                syllabus.file_path, syllabus.file_type
            )

            syllabus.extracted_text = extracted_text
            syllabus.status = "processing"

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

            logger.info(f"Syllabus {syllabus.id} processed successfully")
            return parsed_data
        except Exception as e:
            logger.error(f"Error processing syllabus {syllabus.id}: {e}")
            syllabus.status = "failed"
            raise

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

        await db.commit()
        logger.info(f"Created subjects/chapters for syllabus {syllabus.id}")
