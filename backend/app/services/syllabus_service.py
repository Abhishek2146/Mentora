"""
Syllabus service for Mentora.

Handles syllabus-related business logic.
SQLAlchemy models are defined in app.models.syllabus.
"""

import os
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.documents import Document

from app.core.logger import get_logger
from app.models.syllabus import Syllabus, Subject, Chapter
from app.schemas.syllabus import SyllabusStatus
from langchain_core.documents import Document
from app.services.llm_service import LLMService
from app.services.ocr_service import OCRService
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService
from app.services.syllabus_structure import (
    build_course_overview_document,
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


def _extract_credit_hours(text: str) -> Optional[int]:
    """Extract credit hour information from syllabus text.

    Looks for patterns like:
    - "Credit Hours: 3"
    - "credits: 3"
    - "3 Credit Hours"
    - "Total Credits: 120"
    - "Credit: 3"
    Returns the integer value or None if not found.
    """
    if not text or not text.strip():
        return None

    # Pattern: "Credit Hours: N" or "credits: N" (case-insensitive)
    patterns = [
        r"credit[s]?\s*[:\-]?\s*(\d+)",
        r"[\w\s]*credit[s]?[\w\s]*[:\-]?\s*(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _coerce_int(match.group(1))

    # Pattern: "N Credits" at end of line or sentence
    match = re.search(r"^(\d+)\s+credits?$", text, re.IGNORECASE | re.MULTILINE)
    if match:
        return _coerce_int(match.group(1))

    # Pattern: "N Hrs." or "N Hours" that might be credit hours
    match = re.search(r"\((\d+)\s+[Hh]rs?\)", text)
    if match:
        return _coerce_int(match.group(1))

    return None


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

    async def search_syllabuses(
        self,
        db: AsyncSession,
        user_id: int,
        query: str,
        search_in: Optional[List[str]] = None,
        status: Optional[SyllabusStatus] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Search syllabuses for a user.

        Args:
            db: Database session
            user_id: User ID
            query: Search query string
            search_in: List of fields to search in (title, description, extracted_text, subjects, chapters, topics)
            status: Optional status filter
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Dictionary with items, total, page, per_page, pages
        """
        # Default search fields if not specified
        if search_in is None:
            search_in = ["title", "description", "extracted_text", "subjects", "chapters", "topics"]

        # Build base query
        base_query = select(Syllabus).where(Syllabus.user_id == user_id)

        # Apply status filter
        if status:
            base_query = base_query.where(Syllabus.status == status.value if hasattr(status, 'value') else status)

        # Build search conditions
        search_conditions = []
        search_lower = query.lower()

        if "title" in search_in:
            search_conditions.append(Syllabus.title.ilike(f"%{search_lower}%"))

        if "description" in search_in:
            search_conditions.append(Syllabus.description.ilike(f"%{search_lower}%"))

        if "extracted_text" in search_in:
            search_conditions.append(Syllabus.extracted_text.ilike(f"%{search_lower}%"))

        if "subjects" in search_in:
            # Search in subject names via subquery
            subject_subquery = select(Subject.syllabus_id).where(
                Subject.name.ilike(f"%{search_lower}%")
            )
            search_conditions.append(Syllabus.id.in_(subject_subquery))

        if "chapters" in search_in:
            # Search in chapter names via subquery
            chapter_subquery = select(Subject.syllabus_id).join(Chapter).where(
                Chapter.name.ilike(f"%{search_lower}%")
            )
            search_conditions.append(Syllabus.id.in_(chapter_subquery))

        if "topics" in search_in:
            # Search in chapter topics (JSON field) via subquery
            # This is more complex as topics is a JSON field
            topic_subquery = select(Subject.syllabus_id).join(Chapter).where(
                Chapter.topics.isnot(None)
            )
            search_conditions.append(Syllabus.id.in_(topic_subquery))

        # Combine search conditions with OR
        if search_conditions:
            base_query = base_query.where(or_(*search_conditions))

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query_with_pagination = base_query.order_by(Syllabus.updated_at.desc())
        query_with_pagination = query_with_pagination.offset((page - 1) * per_page).limit(per_page)

        result = await db.execute(query_with_pagination)
        syllabuses = result.scalars().all()

        # Determine matched fields for each result
        items = []
        for syllabus in syllabuses:
            matched_fields = []
            syllabus_lower = str(syllabus.title or "").lower()
            if search_lower in syllabus_lower:
                matched_fields.append("title")

            if syllabus.description and search_lower in (syllabus.description or "").lower():
                matched_fields.append("description")

            if syllabus.extracted_text and search_lower in (syllabus.extracted_text or "").lower():
                matched_fields.append("extracted_text")

            # Check subjects, chapters, topics
            if "subjects" in search_in or "chapters" in search_in or "topics" in search_in:
                # Load subjects and chapters to check
                from sqlalchemy.orm import selectinload
                detail_result = await db.execute(
                    select(Syllabus)
                    .where(Syllabus.id == syllabus.id)
                    .options(selectinload(Syllabus.subjects).selectinload(Subject.chapters))
                )
                detail_syllabus = detail_result.scalars().first()

                if detail_syllabus:
                    for subject in detail_syllabus.subjects or []:
                        if search_lower in (subject.name or "").lower():
                            matched_fields.append("subjects")
                            break
                        for chapter in subject.chapters or []:
                            if search_lower in (chapter.name or "").lower():
                                matched_fields.append("chapters")
                                break
                            if chapter.topics:
                                topics_str = str(chapter.topics).lower()
                                if search_lower in topics_str:
                                    matched_fields.append("topics")
                                    break
                        if "subjects" in matched_fields or "chapters" in matched_fields or "topics" in matched_fields:
                            break

            items.append({
                "id": syllabus.id,
                "title": syllabus.title,
                "description": syllabus.description,
                "file_type": syllabus.file_type,
                "status": syllabus.status,
                "is_processed": syllabus.is_processed,
                "is_ai_processed": syllabus.is_ai_processed,
                "created_at": syllabus.created_at,
                "updated_at": syllabus.updated_at,
                "matched_fields": list(set(matched_fields))
            })

        pages = (total + per_page - 1) // per_page

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "query": query
        }

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

            # Extract credit hours from the original extracted text
            credit_hours = _extract_credit_hours(extracted_text or "")
            if credit_hours is not None:
                logger.info(
                    f"SYLLABUS {syllabus.id}: extracted credit hours = {credit_hours}"
                )

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
                # Attach extracted credit hours to the parsed data so they
                # are available when subjects are persisted.
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
                # Store credit hours at the syllabus level for access
                if credit_hours is not None:
                    syllabus.credits = credit_hours
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
                credits=syllabus.credits,
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

        unit_number = 0
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
                            "unit_number": unit_number,
                        },
                    )
                )

            for chapter in chapters:
                chapter_name = (chapter.get("name") or "").strip() or "Unknown"
                unit_number += 1
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
                    "unit_number": unit_number,
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

        # Prepend a course-level overview document that aggregates all
        # unit names, topic lists, and credit hours into a single chunk.
        # This ensures broad queries like "what are the main topics covered?"
        # or "how many credit hours?" retrieve relevant context even when
        # RAG_TOP_K is small.
        subjects_for_overview = (parsed_data or {}).get("subjects") or []
        if subjects_for_overview:
            credit_hours: Optional[int] = getattr(syllabus, "credits", None)
            if credit_hours == 0:
                credit_hours = None
            overview_raw = build_course_overview_document(
                syllabus_id=syllabus.id,
                user_id=syllabus.user_id,
                subjects=subjects_for_overview,
                source_name=base_metadata.get("source", "syllabus"),
                credit_hours=credit_hours,
            )
            if overview_raw:
                overview_doc = Document(
                    page_content=overview_raw["content"],
                    metadata=overview_raw["metadata"],
                )
                # Insert at the front so it gets index 0 (chunk_index assigned below)
                documents = [overview_doc] + list(documents)
                logger.info(
                    "[Syllabus] Course overview document added for syllabus %s "
                    "(%d chars)",
                    syllabus.id,
                    len(overview_raw["content"]),
                )

        try:
            chunks = documents

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

        # Extract credit hours from the syllabus object if available
        credit_hours: Optional[int] = getattr(syllabus, "credits", None)
        if credit_hours == 0:
            credit_hours = None

        # Course-level overview: one document that answers "what are the main
        # topics?" and "how many credit hours?" without requiring many per-unit
        # chunks to be assembled.
        overview_doc = build_course_overview_document(
            syllabus_id=syllabus.id,
            user_id=syllabus.user_id,
            subjects=subjects,
            source_name=source_name,
            credit_hours=credit_hours,
        )

        unit_docs = build_unit_rag_documents(
            syllabus_id=syllabus.id,
            user_id=syllabus.user_id,
            subjects=subjects,
            source_name=source_name,
        )

        all_raw_docs = []
        if overview_doc:
            all_raw_docs.append(overview_doc)
        all_raw_docs.extend(unit_docs)

        chunks = [
            Document(page_content=d["content"], metadata=d["metadata"])
            for d in all_raw_docs
        ]
        for idx, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = idx
        return chunks
