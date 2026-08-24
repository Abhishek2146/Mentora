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

from langchain_core.documents import Document

from app.core.logger import get_logger
from app.models.syllabus import Syllabus, Subject, Chapter
from app.schemas.syllabus import SyllabusStatus
from app.services.llm_service import LLMService
from app.services.ocr_service import OCRService
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService
from app.services.syllabus_structure import (
    build_unit_rag_documents,
    clean_parsed_syllabus,
    try_regex_parse,
)

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

    async def process_syllabus(self, db: AsyncSession, syllabus: Syllabus) -> dict:
        """Process uploaded syllabus file: OCR extraction + LLM parsing."""
        try:
            filename = os.path.basename(syllabus.file_path) if syllabus.file_path else "unknown"
            logger.info(f"SYLLABUS UPLOAD filename={filename} file_type={syllabus.file_type}")

            extracted_text = await self.ocr_service.extract_text(
                syllabus.file_path, syllabus.file_type
            )

            text_len = len(extracted_text) if extracted_text else 0
            logger.info(f"OCR EXTRACTION characters={text_len}")
            if extracted_text:
                preview = extracted_text[:500].replace("\n", " ")
                logger.info(f"EXTRACTED TEXT PREVIEW: {preview}")

            syllabus.extracted_text = extracted_text
            syllabus.status = "processing"

            if not extracted_text or not extracted_text.strip():
                syllabus.status = "failed"
                logger.error(f"Syllabus {syllabus.id}: no text could be extracted from the file")
                raise ValueError("Unable to extract text from the uploaded syllabus.")

            # Try deterministic regex extraction first — it never
            # hallucinates and works for syllabi with "Unit N:" headings.
            parsed_data = try_regex_parse(extracted_text)
            if parsed_data:
                logger.info(
                    "Syllabus %s: regex extraction succeeded", syllabus.id
                )
            else:
                logger.info(
                    "Syllabus %s: regex extraction did not match; "
                    "falling back to LLM parsing", syllabus.id,
                )
                logger.info(f"LLM PARSING sending {text_len} characters")
                try:
                    parsed_data = await self.llm_service.parse_syllabus_content(
                        extracted_text
                    )
                except Exception as e:
                    logger.error(
                        f"LLM parsing raised an exception for syllabus {syllabus.id}: {e}"
                    )
                    parsed_data = {}

            raw_parsed_output = parsed_data

            subjects_data = parsed_data.get("subjects") or []
            if subjects_data:
                # Validate/clean BEFORE anything is persisted: reject
                # pseudo-unit headings ("Syllabus", "Objectives", ...),
                # duplicates, and malformed chapters.
                try:
                    parsed_data = clean_parsed_syllabus(parsed_data)
                    subjects_data = parsed_data.get("subjects") or []
                except ValueError as e:
                    logger.warning(
                        "Syllabus %s parse validation failed: %s",
                        syllabus.id, e,
                    )
                    subjects_data = []

            if subjects_data:
                # Keep the raw LLM output for traceability, but store the
                # cleaned structure as the authoritative parsed data.
                syllabus.raw_content = raw_parsed_output
                syllabus.parsed_data = {
                    "subjects": [
                        {
                            "name": s.get("name", ""),
                            "description": s.get("description", ""),
                            "chapters": [
                                {
                                    "name": c.get("name", ""),
                                    "description": c.get("description", ""),
                                    "topics": c.get("topics", []),
                                    "estimated_hours": c.get("estimated_hours", 0),
                                }
                                for c in s.get("chapters", [])
                            ],
                        }
                        for s in subjects_data
                    ]
                }
                syllabus.status = "parsed"

                await self._create_subjects_chapters(db, syllabus, parsed_data)

                num_chapters = sum(len(s.get("chapters", [])) for s in subjects_data)
                num_topics = sum(
                    len(c.get("topics", []) or [])
                    for s in subjects_data
                    for c in s.get("chapters", [])
                )
                logger.info(
                    f"PARSED RESULT subjects={len(subjects_data)} "
                    f"chapters={num_chapters} topics={num_topics}"
                )
            else:
                syllabus.status = "uploaded"
                raw_preview = str(parsed_data.get("raw_text", ""))[:300]
                logger.warning(
                    f"Syllabus {syllabus.id} uploaded but could not be parsed into "
                    f"any subjects. Raw LLM output preview: {raw_preview!r}"
                )

            embedding_ok = await self._embed_for_rag(syllabus, extracted_text, parsed_data)

            if embedding_ok and syllabus.status == "parsed":
                syllabus.status = "rag_ready"
            elif not embedding_ok and extracted_text.strip():
                syllabus.status = "embedding_failed"

            logger.info(
                f"Syllabus {syllabus.id} processing complete, status={syllabus.status}"
            )
            return parsed_data
        except Exception as e:
            logger.error(f"Error processing syllabus {syllabus.id}: {e}")
            syllabus.status = "failed"
            raise

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
        """Create and persist subjects and chapters from validated parsed data."""

        subjects_data = parsed_data.get("subjects", [])

        for order, subj_data in enumerate(subjects_data):
            subject_name = (
                str(subj_data.get("name") or "").strip()
                or (syllabus.title or "").strip()
                or "Course"
            )
            subject = Subject(
                syllabus_id=syllabus.id,
                name=subject_name[:255],
                description=subj_data.get("description") or None,
                subject_order=order,
            )
            db.add(subject)
            await db.flush()

            logger.info(
                "[DB] Syllabus: id=%s | subject_order=%d | name=%r",
                syllabus.id, order, subject.name,
            )

            chapters_data = subj_data.get("chapters", []) or []
            for chapter_order, chapter_data in enumerate(chapters_data):
                topics_raw = chapter_data.get("topics")
                topics = (
                    [str(t) for t in topics_raw]
                    if isinstance(topics_raw, list)
                    else []
                )
                chapter = Chapter(
                    subject_id=subject.id,
                    name=str(
                        chapter_data.get("name") or f"Unit {chapter_order + 1}"
                    )[:255],
                    description=chapter_data.get("description") or None,
                    chapter_order=chapter_order,
                    topics=topics,
                    estimated_hours=_coerce_int(
                        chapter_data.get("estimated_hours")
                    ),
                )
                db.add(chapter)
                await db.flush()
                logger.info(
                    "[DB] Unit: chapter_id=%s name=%r | hours=%s | topics=%d",
                    chapter.id,
                    chapter.name,
                    chapter.estimated_hours if chapter.estimated_hours else "not stated",
                    len(topics),
                )
                for topic in topics:
                    logger.info("[DB] Topic: %r (unit=%r)", topic, chapter.name)

            logger.info(
                "[Syllabus] created subject '%s' (%d chapters)",
                subject.name,
                len(chapters_data),
            )

        logger.info(
            "[Syllabus] created %d subjects for syllabus %s",
            len(subjects_data),
            syllabus.id,
        )

    async def _embed_for_rag(
        self, syllabus: Syllabus, extracted_text: str, parsed_data: dict
    ) -> bool:
        """Chunk, embed, and store the syllabus content in Chroma.

        When validated parsed structure is available, embeds structured
        documents (one per unit plus one per topic) that carry
        unit/topic metadata so every vector traces back to its place in
        the uploaded syllabus.  Otherwise falls back to chunking the raw
        extracted text with minimal metadata.

        Returns True if embedding succeeded, False otherwise.
        """

        if not extracted_text or not extracted_text.strip():
            logger.warning(
                "[Syllabus] syllabus %s has no extracted text; skipping RAG embedding",
                syllabus.id,
            )
            return False

        base_metadata = {
            "user_id": syllabus.user_id,
            "syllabus_id": syllabus.id,
            "source": os.path.basename(syllabus.file_path)
            if syllabus.file_path
            else "unknown",
        }

        try:
            chunks = self._build_rag_chunks(syllabus, parsed_data)

            if not chunks:
                # Parsing produced nothing usable - fall back to raw text
                # chunks so retrieval still has something to work with.
                logger.warning(
                    "[VECTOR] Syllabus %s: no structured units; embedding "
                    "raw text fallback",
                    syllabus.id,
                )
                chunks = self.embedding_service.chunk_text_with_metadata(
                    extracted_text, base_metadata
                )

            if not chunks:
                logger.warning(
                    "[Syllabus] No chunks produced for syllabus %s",
                    syllabus.id,
                )
                return False

            collection_name = (
                self.vector_service.collection_name_for_syllabus(syllabus.id)
            )

            # Delete any existing collection for this syllabus so that
            # re-processing (e.g. re-upload or re-analyze) does not leave
            # stale/duplicate vectors behind.  This makes embedding idempotent.
            self.vector_service.delete_collection(collection_name)

            self.vector_service.add_documents(collection_name, chunks)
            syllabus.is_ai_processed = True

            logger.info(
                "[VECTOR] embedded %d chunks for syllabus %s into collection '%s'",
                len(chunks),
                syllabus.id,
                collection_name,
            )
            return True

        except Exception as e:
            syllabus.is_ai_processed = False
            logger.error(
                "[Syllabus] RAG embedding failed for syllabus %s: %s",
                syllabus.id,
                e,
            )
            return False

    def _build_rag_chunks(
        self, syllabus: Syllabus, parsed_data: dict
    ) -> List[Document]:
        """Build traceable RAG documents from validated parsed structure.

        Every document carries metadata: user_id, syllabus_id, course,
        unit_number, unit_title, topic_title and source, so retrieval can
        be filtered by course/syllabus and grounded answers can cite
        exactly where each fact came from.  Returns [] when there is no
        usable parsed structure (caller falls back to raw text chunks).
        """
        subjects = (parsed_data or {}).get("subjects") or []
        if not subjects:
            return []

        source_name = (
            os.path.basename(syllabus.file_path)
            if syllabus.file_path
            else "syllabus"
        )
        unit_docs = build_unit_rag_documents(
            syllabus_id=syllabus.id,
            user_id=syllabus.user_id,
            subjects=subjects,
            source_name=source_name,
        )
        chunks = [
            Document(page_content=d["content"], metadata=d["metadata"])
            for d in unit_docs
        ]
        for idx, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = idx
        return chunks
