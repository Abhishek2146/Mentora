"""
Tutor (AI Chatbot) Service
"""
import json
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logger import get_logger
from app.models.chat_history import ChatSession, ChatMessage
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService

logger = get_logger(__name__)


class TutorService:
    def __init__(self):
        self.llm_service = LLMService()
        self.vector_service = VectorService()

    async def process_message(
        self,
        user_id: int,
        message: str,
        syllabus_id: Optional[int] = None,
        session_id: Optional[int] = None,
        db: AsyncSession = None,
    ) -> dict:
        """Process a user message and return AI response."""
        if session_id:
            session_result = await db.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id, ChatSession.user_id == user_id
                )
            )
            session = session_result.scalars().first()
        else:
            session = ChatSession(
                user_id=user_id,
                title=message[:50] + "..." if len(message) > 50 else message,
                syllabus_id=syllabus_id,
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

        messages = [{"role": "user", "content": message}]

        context_docs = []
        if syllabus_id:
            collection_name = f"syllabus_{syllabus_id}"
            try:
                context_docs = self.vector_service.similarity_search(collection_name, message, k=3)
            except Exception:
                pass

        context = "\n".join([doc.page_content for doc in context_docs]) if context_docs else ""

        if context:
            system_msg = {
                "role": "system",
                "content": f"You are a helpful AI tutor. Use this context to answer:\n\n{context}",
            }
            messages = [system_msg] + messages

        ai_response = await self.llm_service.chat_completion(messages, temperature=0.7)

        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=message,
            sequence=1,
        )
        db.add(user_msg)

        ai_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=ai_response,
            sequence=2,
        )
        db.add(ai_msg)

        await db.commit()

        return {"response": ai_response, "session_id": session.id}
