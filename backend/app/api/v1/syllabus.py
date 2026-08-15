"""
Syllabus API endpoints
"""
import os
from typing import List, Optional

import pytesseract
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user_id
from app.core.config import settings
from app.database.database import get_db
from app.models.syllabus import Syllabus, Subject, Chapter
from app.schemas.syllabus import SyllabusCreate, SyllabusOut, SyllabusUpdate, SyllabusStatus
from app.services.syllabus_service import SyllabusService

router = APIRouter()
syllabus_service = SyllabusService()


@router.post("/", response_model=SyllabusOut, status_code=status.HTTP_201_CREATED)
@router.post("/upload", response_model=SyllabusOut, status_code=status.HTTP_201_CREATED)
async def upload_syllabus(
    title: str = Form(...),
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    file_ext = file.filename.rsplit(".", 1)[-1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS.split(","):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type .{file_ext} not allowed",
        )

    upload_dir = os.path.join(settings.UPLOAD_DIR, "syllabus")
    os.makedirs(upload_dir, exist_ok=True)
    file_name = f"{user_id}_{title.replace(' ', '_')}.{file_ext}"
    file_path = os.path.join(upload_dir, file_name)

    with open(file_path, "wb") as f:
        content = await file.read()
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
    await db.refresh(new_syllabus)

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

    result = await db.execute(
        select(Syllabus)
        .where(Syllabus.id == new_syllabus.id)
        .options(
            selectinload(Syllabus.subjects).selectinload(Subject.chapters)
        )
    )
    syllabus = result.scalars().first()

    return syllabus


@router.get("/", response_model=List[SyllabusOut])
async def list_syllabuses(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Syllabus).where(Syllabus.user_id == user_id).offset(skip).limit(limit)
    )
    return result.scalars().all()


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

    result = await db.execute(
        select(Syllabus)
        .where(Syllabus.id == syllabus.id)
        .options(
            selectinload(Syllabus.subjects).selectinload(Subject.chapters)
        )
    )
    return result.scalars().first()


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
