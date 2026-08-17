"""
AI Tutor API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.chat_history import ChatSession, ChatMessage
from app.services.tutor_service import TutorService

router = APIRouter()
tutor_service = TutorService()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The student's question")
    syllabus_id: Optional[int] = None
    session_id: Optional[int] = None
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    session_id: int


@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await tutor_service.process_message(
        user_id=user_id,
        message=request.message,
        syllabus_id=request.syllabus_id,
        session_id=request.session_id or request.conversation_id,
        db=db,
    )
    return result


@router.get("/sessions", response_model=List)
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == user_id)
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}/messages", response_model=List)
async def get_session_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages_result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id)
    )
    return messages_result.scalars().all()


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await db.delete(session)
    await db.commit()
    return None
