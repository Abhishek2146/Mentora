"""
Voice Learning API endpoints
"""

from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.services.voice_service import VoiceService


router = APIRouter()


class VoiceRequest(BaseModel):
    message: str
    syllabus_id: Optional[int] = None
    session_id: Optional[int] = None
    voice: str = "default"


class VoiceResponse(BaseModel):
    transcript: str
    response: str
    audio_url: Optional[str] = None


@router.post("/listen", response_model=VoiceResponse)
async def voice_learning(
    audio: UploadFile = File(...),
    syllabus_id: Optional[int] = None,
    session_id: Optional[int] = None,
    voice: str = "default",
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    voice_service = VoiceService()

    audio_content = await audio.read()

    result = await voice_service.process_voice_input(
        user_id=user_id,
        audio_content=audio_content,
        syllabus_id=syllabus_id,
        session_id=session_id,
        voice=voice,
        db=db,
    )

    return result


@router.post("/speak", response_model=dict)
async def text_to_speech(
    text: str,
    voice: str = "default",
):
    voice_service = VoiceService()

    audio_url = await voice_service.text_to_speech(
        text,
        voice,
    )

    return {
        "audio_url": audio_url,
        "text": text,
    }


@router.get("/sessions", response_model=list)
async def get_voice_sessions(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    voice_service = VoiceService()

    return await voice_service.get_user_sessions(
        user_id,
        db,
    )