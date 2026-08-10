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

    async def process_syllabus(self, syllabus: Syllabus) -> dict:
        """Process uploaded syllabus file: OCR extraction + LLM parsing."""
        try:
            extracted_text = await self.ocr_service.extract_text(
                syllabus.file_path, syllabus.file_type
            )

            syllabus.extracted_text = extracted_text
            syllabus.status = "processing"

            parsed_data = await self.llm_service.parse_syllabus_content(extracted_text)
            syllabus.parsed_data = parsed_data
            syllabus.status = "parsed"

            await self._create_subjects_chapters(syllabus, parsed_data)

            logger.info(f"Syllabus {syllabus.id} processed successfully")
            return parsed_data
        except Exception as e:
            logger.error(f"Error processing syllabus {syllabus.id}: {e}")
            syllabus.status = "failed"
            raise

    async def _create_subjects_chapters(self, syllabus: Syllabus, parsed_data: dict):
        """Create subjects and chapters from parsed data."""
        subjects_data = parsed_data.get("subjects", [])
        order = 0
        for subj_data in subjects_data:
            subject = Subject(
                syllabus_id=syllabus.id,
                name=subj_data.get("name", f"Subject {order + 1}"),
                description=subj_data.get("description"),
                order=order,
            )
            order += 1
        logger.info(f"Created subjects/chapters for syllabus {syllabus.id}")
