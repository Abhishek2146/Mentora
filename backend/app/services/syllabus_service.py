"""
Syllabus service for Mentora.

Handles syllabus-related business logic.
SQLAlchemy models are defined in app.models.syllabus.
"""

import os
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.syllabus import Syllabus, Subject, Chapter
from app.schemas.syllabus import SyllabusStatus
from langchain_core.documents import Document
from app.services.llm_service import LLMService
from app.services.ocr_service import OCRService
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService

logger = get_logger(__name__)


def _coerce_int(value: Any) -> int:
    """Best-effort conversion of an LLM-provided hours value to int.

    The LLM may return an int, a numeric string, or a phrase like
    "3 Hrs.".  This normalises everything to a plain integer (0 when
    no usable number is found).
    """
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group())
    return 0


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

    async def get_syllabus_with_details(
        self,
        db: AsyncSession,
        syllabus_id: int,
        user_id: int,
    ):
        """Get a syllabus with eagerly-loaded subjects, chapters, and topics."""

        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Syllabus)
            .where(
                Syllabus.id == syllabus_id,
                Syllabus.user_id == user_id,
            )
            .options(
                selectinload(Syllabus.subjects).selectinload(Subject.chapters)
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

    async def process_syllabus(
        self, db: AsyncSession, syllabus: Syllabus
    ) -> Dict[str, Any]:
        """Process uploaded syllabus file: OCR extraction + LLM parsing.

        Steps:
        1. Extract text from the stored file (OCR or pypdf).
        2. Parse the extracted text with the LLM into structured
           subjects/chapters/topics.
        3. Persist parsed_data, subjects, and chapters on the Syllabus
           record (clearing any previous results first to avoid
           duplicates on re-analysis).
        4. Embed the extracted text into Chroma for RAG.
        5. Commit the final status.

        Returns a dict with ``status`` and ``parsed_data``.
        """

        logger.info(
            "[Syllabus] processing syllabus %s (file_type=%s)",
            syllabus.id,
            syllabus.file_type,
        )

        # Verify the file actually exists on disk before calling OCR.
        file_exists = syllabus.file_path and os.path.exists(syllabus.file_path)
        logger.info("[Syllabus] File exists: %s", file_exists)
        logger.info("[Syllabus] File path: %s", syllabus.file_path)
        logger.info("[Syllabus] File type: %s", syllabus.file_type)

        if not file_exists:
            syllabus.status = SyllabusStatus.FAILED.value
            syllabus.processing_error = (
                f"File not found on disk: {syllabus.file_path}"
            )
            await db.commit()
            return {
                "status": syllabus.status,
                "error": f"File not found: {syllabus.file_path}",
                "parsed_data": None,
            }

        # --- Step 1: Extract text ----------------------------------------
        try:
            extracted_text = await self.ocr_service.extract_text(
                syllabus.file_path, syllabus.file_type
            )
        except Exception as e:
            logger.error(
                "[Syllabus] OCR extraction failed for syllabus %s: %s",
                syllabus.id,
                e,
            )
            syllabus.status = SyllabusStatus.FAILED.value
            syllabus.processing_error = f"OCR extraction failed: {e}"
            await db.commit()
            return {
                "status": syllabus.status,
                "error": str(e),
                "parsed_data": None,
            }

        logger.info(
            "[Syllabus] OCR extracted %d characters for syllabus %s",
            len(extracted_text),
            syllabus.id,
        )
        logger.info(
            "[Syllabus] OCR preview: %s",
            extracted_text[:500],
        )

        if not extracted_text or not extracted_text.strip():
            logger.warning(
                "[Syllabus] No text extracted for syllabus %s",
                syllabus.id,
            )
            syllabus.extracted_text = ""
            syllabus.status = SyllabusStatus.FAILED.value
            syllabus.processing_error = "No text could be extracted from the file."
            await db.commit()
            return {
                "status": syllabus.status,
                "error": "No text could be extracted from the file.",
                "parsed_data": None,
            }

        logger.info(
            "[Syllabus] OCR extracted %d characters for syllabus %s",
            len(extracted_text),
            syllabus.id,
        )
        syllabus.extracted_text = extracted_text
        syllabus.status = SyllabusStatus.PROCESSING.value
        await db.commit()

        # --- Step 2: Parse with LLM --------------------------------------
        parsed_data: Optional[dict] = None
        parse_error: Optional[str] = None
        try:
            parsed_data = await self.llm_service.parse_syllabus_content(
                extracted_text
            )
        except Exception as e:
            logger.error(
                "[Syllabus] LLM parsing failed for syllabus %s: %s",
                syllabus.id,
                e,
            )
            parse_error = f"LLM parsing failed: {e}"

        if parsed_data:
            logger.info(
                "[Syllabus] Parsed data: %s",
                parsed_data,
            )
        else:
            logger.warning(
                "[Syllabus] LLM parsing produced no valid data for "
                "syllabus %s; building fallback structure",
                syllabus.id,
            )

        # --- Step 3: Persist parsed structure ----------------------------
        try:
            await self._clear_existing_subjects(db, syllabus.id)

            if parsed_data and parsed_data.get("subjects"):
                await self._create_subjects_chapters(db, syllabus, parsed_data)
                syllabus.parsed_data = parsed_data
                syllabus.status = SyllabusStatus.PARSED.value
                syllabus.processing_error = None
            else:
                # LLM parsing failed or returned empty -- build a fallback
                # structure from the extracted text so the syllabus always
                # has usable subject/chapter/topic data.
                fallback_data = self._build_fallback_structure(
                    extracted_text, syllabus.title
                )
                await self._create_subjects_chapters(db, syllabus, fallback_data)
                syllabus.parsed_data = fallback_data
                syllabus.status = SyllabusStatus.PARSED.value
                syllabus.processing_error = parse_error

                logger.info(
                    "[Syllabus] Created fallback structure (%d subjects) "
                    "for syllabus %s",
                    len(fallback_data.get("subjects", [])),
                    syllabus.id,
                )

            await db.commit()

            subject_count = len(
                (syllabus.parsed_data or {}).get("subjects", [])
            )
            logger.info(
                "[Syllabus] Parsed %d subjects for syllabus %s",
                subject_count,
                syllabus.id,
            )

        except Exception as e:
            logger.error(
                "[Syllabus] Failed to persist parsed data for syllabus %s: %s",
                syllabus.id,
                e,
            )
            syllabus.status = SyllabusStatus.FAILED.value
            syllabus.processing_error = f"Failed to persist parsed data: {e}"
            await db.commit()
            # Even on persistence failure, still embed the text for RAG.

        # --- Step 4: Embed for RAG ---------------------------------------
        # Always embed the extracted text, even if LLM parsing failed.
        # This ensures the tutor can retrieve content from Chroma.
        try:
            await self._embed_for_rag(
                syllabus, extracted_text, syllabus.parsed_data or {}
            )
            syllabus.is_ai_processed = True
            syllabus.is_processed = True
            await db.commit()
        except Exception as e:
            logger.error(
                "[Syllabus] RAG embedding failed for syllabus %s: %s",
                syllabus.id,
                e,
            )
            syllabus.is_ai_processed = False
            await db.commit()

        return {
            "status": syllabus.status,
            "parsed_data": syllabus.parsed_data,
        }

    @staticmethod
    def _build_fallback_structure(text: str, title: str = "Syllabus") -> dict:
        """Build a minimal syllabus structure from extracted text.

        Used as a fallback when LLM parsing fails, so the syllabus always
        has usable subject/chapter/topic data for display and retrieval.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # Try to identify unit/module headings.
        # Matches lines like "Unit 1: Title (3 Hrs.)" or "Module A - Topic"
        unit_pattern = re.compile(
            r"^(?:Unit|Module|Chapter|Part|Week)\s+\S+"
            r"\s*[:\-]?\s*(.+?)"
            r"(?:\s*\((\d+(?:\.\d+)?)\s*(?:Hrs?|Hours?)\))?\s*$",
            re.IGNORECASE,
        )

        subjects: List[dict] = []
        current_subject: Optional[dict] = None
        current_chapter: Optional[dict] = None

        for line in lines:
            match = unit_pattern.match(line)
            if match:
                unit_title = match.group(1).strip()
                hours_str = match.group(2)
                estimated_hours = (
                    int(float(hours_str)) if hours_str else 0
                )

                current_subject = {
                    "name": unit_title,
                    "description": "",
                    "chapters": [],
                }
                subjects.append(current_subject)
                current_chapter = {
                    "name": f"{unit_title} Overview",
                    "description": "",
                    "topics": [],
                    "estimated_hours": estimated_hours,
                }
                current_subject["chapters"].append(current_chapter)
            elif current_chapter is not None:
                # Non-heading line: likely a topic or sub-heading
                topic = re.sub(r"^[-*\d.\t\s]+", "", line).strip()
                if topic:
                    current_chapter["topics"].append(topic)

        # If no unit headings were found, build a single subject
        # from the first chunk of the text.
        if not subjects:
            topics = lines[:20] if lines else [text[:200]]
            subjects = [
                {
                    "name": title,
                    "description": "Extracted from syllabus document",
                    "chapters": [
                        {
                            "name": "Syllabus Content",
                            "description": "",
                            "topics": topics,
                            "estimated_hours": 0,
                        }
                    ],
                }
            ]

        return {"subjects": subjects}

    async def _clear_existing_subjects(
        self, db: AsyncSession, syllabus_id: int
    ):
        """Delete existing Subject (and their Chapter) rows for a syllabus
        before re-creating them.  This prevents duplicates when
        ``process_syllabus`` is called more than once (e.g. upload + analyze).
        """
        await db.execute(
            delete(Chapter).where(Chapter.subject_id.in_(
                select(Subject.id).where(Subject.syllabus_id == syllabus_id)
            ))
        )
        await db.execute(
            delete(Subject).where(Subject.syllabus_id == syllabus_id)
        )
        await db.flush()

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
                     estimated_hours=_coerce_int(
                         chapter_data.get("estimated_hours")
                     ),
                 )
                db.add(chapter)

            logger.info(
                "[Syllabus] created subject '%s' (%d chapters)",
                subject.name,
                len(subj_data.get("chapters", [])),
            )

        logger.info(
            "[Syllabus] created %d subjects for syllabus %s",
            len(subjects_data),
            syllabus.id,
        )

    def _build_structured_documents(
        self, parsed_data: dict, base_metadata: dict
    ) -> List[Document]:
        """Build chapter-aware RAG documents from the parsed syllabus
        structure so retrieved chunks carry subject/chapter metadata.

        Produces one "chapter list" document per subject (so queries like
        "what are the chapters?" retrieve the full list) and one document
        per chapter containing its description and topics.  Returns an
        empty list when there is no usable structure, in which case the
        caller falls back to plain full-text chunking.
        """
        documents: List[Document] = []
        subjects = (parsed_data or {}).get("subjects") or []

        for subject in subjects:
            subject_name = (subject.get("name") or "").strip() or "Unknown"
            chapters = subject.get("chapters") or []

            chapter_names = [
                (ch.get("name") or "").strip()
                for ch in chapters
                if (ch.get("name") or "").strip()
            ]
            if chapter_names:
                listing_content = (
                    f"Chapter list for subject {subject_name}:\n"
                    + "\n".join(f"- {name}" for name in chapter_names)
                )
                documents.extend(
                    self.embedding_service.chunk_text_with_metadata(
                        listing_content,
                        {
                            **base_metadata,
                            "subject": subject_name,
                            "chapter": "",
                            "topic": "",
                            "doc_type": "chapter_list",
                        },
                    )
                )

            for chapter in chapters:
                chapter_name = (chapter.get("name") or "").strip() or "Unknown"
                parts: List[str] = []
                description = (chapter.get("description") or "").strip()
                if description:
                    parts.append(description)
                topics = chapter.get("topics") or []
                for topic in topics:
                    topic = str(topic).strip()
                    if topic:
                        parts.append(f"- {topic}")

                content = "\n".join(parts).strip()
                if not content:
                    content = f"{subject_name}: {chapter_name}"

                metadata = {
                    **base_metadata,
                    "subject": subject_name,
                    "chapter": chapter_name,
                    "topic": "",
                    "doc_type": "chapter",
                }
                docs = self.embedding_service.chunk_text_with_metadata(
                    content, metadata
                )
                if not docs:
                    docs = [Document(page_content=content, metadata=metadata)]
                documents.extend(docs)

        return documents

    async def _embed_for_rag(
        self, syllabus: Syllabus, extracted_text: str, parsed_data: dict
    ) -> None:
        """Chunk, embed, and store the syllabus text in Chroma."""

        if not extracted_text or not extracted_text.strip():
            logger.warning(
                "[Syllabus] syllabus %s has no extracted text; skipping RAG embedding",
                syllabus.id,
            )
            return

        base_metadata = {
            "user_id": syllabus.user_id,
            "syllabus_id": syllabus.id,
            "source": os.path.basename(syllabus.file_path)
            if syllabus.file_path
            else "unknown",
        }

        # Build chapter-aware documents from the parsed structure so every
        # chunk carries subject/chapter metadata and the tutor can answer
        # structural questions (chapter lists, per-chapter summaries).
        # Fall back to plain full-text chunking when there is no structure.
        documents = self._build_structured_documents(
            parsed_data, base_metadata
        )
        if not documents:
            documents = self.embedding_service.chunk_text_with_metadata(
                extracted_text, base_metadata
            )

        try:
            chunks = documents

            if not chunks:
                logger.warning(
                    "[Syllabus] No chunks produced for syllabus %s",
                    syllabus.id,
                )
                return

            collection_name = (
                self.vector_service.collection_name_for_syllabus(syllabus.id)
            )

            # Delete any existing collection for this syllabus so that
            # re-processing (e.g. re-upload or re-analyze) does not leave
            # stale/duplicate vectors behind.  This makes embedding idempotent.
            self.vector_service.delete_collection(collection_name)

            self.vector_service.add_documents(collection_name, chunks)

            logger.info(
                "[Syllabus] embedded %d chunks for syllabus %s into collection '%s'",
                len(chunks),
                syllabus.id,
                collection_name,
            )

        except Exception as e:
            logger.error(
                "[Syllabus] RAG embedding failed for syllabus %s: %s",
                syllabus.id,
                e,
            )
            raise
