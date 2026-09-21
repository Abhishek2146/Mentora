"""
Re-index all existing syllabi to v4 RAG format.

This script reads the already-parsed syllabus data from the database and
rebuilds the Chroma vector index WITHOUT re-running OCR or LLM parsing.
It adds the new course-level overview document (all units + topics + credit
hours) that fixes:
  - Bug 1: Tutor refusing to answer credit-hour questions
  - Bug 2: Tutor returning only the last unit's topics for "main topics" queries

Usage (from the backend/ directory with venv activated):
    python reindex_syllabi.py

    # Optional: only re-index a specific syllabus by ID
    python reindex_syllabi.py --syllabus-id 2
"""

import asyncio
import argparse
import os
import sys
from typing import Optional

# Ensure the backend app package is importable.
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logger import get_logger
from app.database.database import AsyncSessionLocal
from app.models.syllabus import Syllabus
from app.services.vector_service import VectorService
from app.services.embedding_service import EmbeddingService
from app.services.syllabus_structure import (
    build_course_overview_document,
    build_unit_rag_documents,
)

logger = get_logger("reindex_syllabi")


def _build_documents_from_parsed(
    syllabus: Syllabus,
    parsed_data: dict,
) -> list:
    """Build v4 RAG documents from stored parsed_data.

    Returns a list of langchain Documents.
    """
    subjects = (parsed_data or {}).get("subjects") or []
    if not subjects:
        logger.warning(
            "Syllabus %d (%s): no subjects in parsed_data, skipping",
            syllabus.id, syllabus.title,
        )
        return []

    source_name = (
        os.path.basename(syllabus.file_path)
        if syllabus.file_path
        else "syllabus"
    )

    # Credit hours: may be stored as a dynamic attribute from process_syllabus
    credit_hours: Optional[int] = getattr(syllabus, "credits", None)
    if credit_hours == 0:
        credit_hours = None

    # --- Course-level overview document (the new addition in v4) ---
    overview_raw = build_course_overview_document(
        syllabus_id=syllabus.id,
        user_id=syllabus.user_id,
        subjects=subjects,
        source_name=source_name,
        credit_hours=credit_hours,
    )

    # --- Per-unit + per-topic documents (same as v3) ---
    unit_raw_docs = build_unit_rag_documents(
        syllabus_id=syllabus.id,
        user_id=syllabus.user_id,
        subjects=subjects,
        source_name=source_name,
    )

    all_raw = []
    if overview_raw:
        all_raw.append(overview_raw)
    all_raw.extend(unit_raw_docs)

    documents = [
        Document(page_content=d["content"], metadata=d["metadata"])
        for d in all_raw
    ]
    for idx, doc in enumerate(documents):
        doc.metadata["chunk_index"] = idx

    return documents


async def reindex_all(target_syllabus_id: Optional[int] = None) -> None:
    vector_service = VectorService()

    async with AsyncSessionLocal() as db:
        query = select(Syllabus)
        if target_syllabus_id is not None:
            query = query.where(Syllabus.id == target_syllabus_id)
        result = await db.execute(query)
        syllabi = result.scalars().all()

    if not syllabi:
        logger.info("No syllabi found.")
        return

    logger.info(
        "Re-indexing %d syllabus(es) to RAG v%s ...",
        len(syllabi), settings.RAG_INDEX_VERSION,
    )

    success = 0
    skipped = 0
    failed = 0

    for syllabus in syllabi:
        parsed_data = syllabus.parsed_data or {}
        subjects = parsed_data.get("subjects") or []

        if not subjects:
            logger.warning(
                "Syllabus %d (%s): no parsed_data — run 'Analyze' in the app "
                "or re-upload to parse it first.",
                syllabus.id, syllabus.title,
            )
            skipped += 1
            continue

        logger.info(
            "Syllabus %d (%s): building documents ...",
            syllabus.id, syllabus.title,
        )

        try:
            documents = _build_documents_from_parsed(syllabus, parsed_data)
            if not documents:
                skipped += 1
                continue

            collection_name = vector_service.collection_name_for_syllabus(syllabus.id)

            # Delete old collection (old version) and write fresh one.
            vector_service.delete_collection(collection_name)
            vector_service.add_documents(collection_name, documents)

            logger.info(
                "  OK: syllabus %d — %d documents indexed into '%s'",
                syllabus.id, len(documents), collection_name,
            )
            success += 1
        except Exception as e:
            logger.error(
                "  FAILED: syllabus %d (%s): %s",
                syllabus.id, syllabus.title, e,
            )
            failed += 1

    print()
    print(f"Re-indexing complete: {success} succeeded, {skipped} skipped, {failed} failed.")
    if skipped:
        print(
            "Skipped syllabi have no parsed_data. "
            "Re-upload them in the Mentora app to parse and index them."
        )


def main():
    parser = argparse.ArgumentParser(description="Re-index Mentora syllabi to v4 RAG format")
    parser.add_argument(
        "--syllabus-id",
        type=int,
        default=None,
        help="Re-index only this syllabus ID (omit to re-index all)",
    )
    args = parser.parse_args()
    asyncio.run(reindex_all(args.syllabus_id))


if __name__ == "__main__":
    main()
