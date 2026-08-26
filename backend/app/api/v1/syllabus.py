"""
Syllabus API endpoints
"""
import os
from typing import List, Optional

import pytesseract
import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user_id
from app.core.config import settings
from app.database.database import get_db
from app.models.syllabus import Syllabus, Subject, Chapter
from app.schemas.syllabus import (
    SyllabusCreate, SyllabusOut, SyllabusUpdate, SyllabusStatus,
    SyllabusSearchRequest, SyllabusSearchResponse
)
from app.services.syllabus_service import SyllabusService

router = APIRouter()
syllabus_service = SyllabusService()

logger = logging.getLogger(__name__)


@router.post("/", response_model=SyllabusOut, status_code=status.HTTP_201_CREATED)
@router.post("/upload", response_model=SyllabusOut, status_code=status.HTTP_201_CREATED)
async def upload_syllabus(
    title: str = Form(...),
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    logger.info(
        "[UploadSyllabus] Received upload: title=%s, filename=%s, content_type=%s",
        title,
        file.filename,
        file.content_type,
    )

    file_ext = file.filename.rsplit(".", 1)[-1].lower()
    logger.info("[UploadSyllabus] Detected file_ext: %s", file_ext)

    if file_ext not in settings.ALLOWED_EXTENSIONS.split(","):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type .{file_ext} not allowed",
        )

    # Strip a trailing extension from the title so we don't end up with
    # double extensions like "syllabus.pdf.pdf".  Users often provide the
    # file name (including extension) as the title.
    safe_title = title.strip()
    if safe_title.lower().endswith(f".{file_ext}"):
        safe_title = safe_title[: -(len(file_ext) + 1)]
    safe_title = safe_title.replace(" ", "_")
    logger.info("[UploadSyllabus] safe_title: %s", safe_title)

    upload_dir = os.path.join(settings.UPLOAD_DIR, "syllabus")
    os.makedirs(upload_dir, exist_ok=True)

    # Enforce max upload size if the SpooledTemporaryFile reports a size.
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is too large.",
        )

    file_name = f"{user_id}_{safe_title}.{file_ext}"
    file_path = os.path.join(upload_dir, file_name)

    with open(file_path, "wb") as f:
        f.write(content)

    new_syllabus = Syllabus(
        user_id=user_id,
        title=title,
        description=description,
        file_path=file_path,
        file_type=file_ext,
        status=SyllabusStatus.UPLOADED.value,
    )
    db.add(new_syllabus)
    await db.commit()
    # NOTE: intentionally skip db.refresh(new_syllabus).
    # With expire_on_commit=False the PK is already populated, and
    # calling refresh would trigger selectin loading of subjects as an
    # empty list (they don't exist yet).  That empty list would then be
    # cached in the identity map and returned by the selectinload query
    # below, causing the response to contain zero subjects.

    try:
        await syllabus_service.process_syllabus(db, new_syllabus)
        await db.commit()
    except pytesseract.TesseractNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "OCR engine (Tesseract) is not installed or not configured. "
                "Contact the administrator to enable syllabus processing."
            ),
        )
    except ValueError as e:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Reload the syllabus with subjects and chapters eager-loaded.
    result = await db.execute(
        select(Syllabus)
        .where(Syllabus.id == new_syllabus.id)
        .options(
            selectinload(Syllabus.subjects).selectinload(Subject.chapters)
        )
        .execution_options(populate_existing=True)
    )
    syllabus = result.scalars().first()

    return syllabus

    if syllabus is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reload syllabus after processing.",
        )

    logger.info(
        "[UploadSyllabus] Response: id=%s, status=%s, title=%s, "
        "subjects_count=%d, parsed_data_keys=%s, is_processed=%s, "
        "is_ai_processed=%s",
        syllabus.id,
        syllabus.status,
        syllabus.title,
        len(syllabus.subjects or []),
        list((syllabus.parsed_data or {}).keys()),
        syllabus.is_processed,
        syllabus.is_ai_processed,
    )
    for subj in syllabus.subjects or []:
        logger.info(
            "[UploadSyllabus] Subject: name=%s, chapters=%d",
            subj.name,
            len(subj.chapters or []),
        )

    return syllabus


@router.get("/", response_model=List[SyllabusOut])
async def list_syllabuses(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Syllabus)
        .where(Syllabus.user_id == user_id)
        .order_by(Syllabus.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/search", response_model=SyllabusSearchResponse)
async def search_syllabuses(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    search_in: Optional[List[str]] = Query(
        None,
        description="Fields to search in: title, description, extracted_text, subjects, chapters, topics"
    ),
    status: Optional[SyllabusStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Search user's syllabuses by query string.
    
    Searches in title, description, extracted text (OCR), subject names, chapter names, and topics.
    """
    result = await syllabus_service.search_syllabuses(
        db=db,
        user_id=user_id,
        query=q,
        search_in=search_in,
        status=status,
        page=page,
        per_page=per_page,
    )
    return result


@router.get("/{syllabus_id}", response_model=SyllabusOut)
async def get_syllabus(
    syllabus_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Syllabus).where(Syllabus.id == syllabus_id, Syllabus.user_id == user_id)
    )
    syllabus = result.scalars().first()
    if not syllabus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Syllabus not found",
        )
    return syllabus


@router.put("/{syllabus_id}", response_model=SyllabusOut)
async def update_syllabus(
    syllabus_id: int,
    syllabus_data: SyllabusUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Syllabus).where(Syllabus.id == syllabus_id, Syllabus.user_id == user_id)
    )
    syllabus = result.scalars().first()
    if not syllabus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Syllabus not found",
        )

    update_data = syllabus_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(syllabus, field, value)

    db.add(syllabus)
    await db.commit()
    await db.refresh(syllabus)
    return syllabus


@router.delete("/{syllabus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_syllabus(
    syllabus_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Syllabus).where(Syllabus.id == syllabus_id, Syllabus.user_id == user_id)
    )
    syllabus = result.scalars().first()
    if not syllabus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Syllabus not found",
        )

    if syllabus.file_path and os.path.exists(syllabus.file_path):
        os.remove(syllabus.file_path)

    await db.delete(syllabus)
    await db.commit()
    return None


@router.post("/{syllabus_id}/analyze", response_model=SyllabusOut)
async def analyze_syllabus(
    syllabus_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Syllabus).where(Syllabus.id == syllabus_id, Syllabus.user_id == user_id)
    )
    syllabus = result.scalars().first()
    if not syllabus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Syllabus not found",
        )

    try:
        await syllabus_service.process_syllabus(db, syllabus)
    except pytesseract.TesseractNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "OCR engine (Tesseract) is not installed or not configured. "
                "Contact the administrator to enable syllabus processing."
            ),
        )

    from app.database.database import AsyncSessionLocal

    async with AsyncSessionLocal() as fresh_db:
        result = await fresh_db.execute(
            select(Syllabus)
            .where(Syllabus.id == syllabus.id)
            .options(
                selectinload(Syllabus.subjects).selectinload(Subject.chapters)
            )
        )
        fresh_syllabus = result.scalars().first()

    if fresh_syllabus is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reload syllabus after analyze.",
        )

    syllabus.subjects = fresh_syllabus.subjects
    return syllabus


@router.get("/{syllabus_id}/subjects", response_model=List)
async def get_syllabus_subjects(
    syllabus_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Subject).join(Syllabus).where(
            Syllabus.id == syllabus_id, Syllabus.user_id == user_id
        )
    )
    return result.scalars().all()
