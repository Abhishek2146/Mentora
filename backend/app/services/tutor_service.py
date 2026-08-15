"""
Tutor (AI Chatbot) Service
"""
import json
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logger import get_logger
from app.models.chat_history import ChatSession, ChatMessage
from app.models.syllabus import Syllabus
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService
from app.services.progress_service import ProgressService

logger = get_logger(__name__)


class TutorService:
    def __init__(self):
        self.llm_service = LLMService()
        self.vector_service = VectorService()
        self.progress_service = ProgressService()

    async def _verify_syllabus_ownership(
        self, db: AsyncSession, syllabus_id: int, user_id: int
    ) -> bool:
        """Confirm the syllabus belongs to the authenticated user before any
        RAG retrieval touches its vector collection."""
        result = await db.execute(
            select(Syllabus).where(
                Syllabus.id == syllabus_id, Syllabus.user_id == user_id
            )
        )
        return result.scalars().first() is not None

    async def _build_personalization_note(
        self, user_id: int, syllabus_id: Optional[int], db: AsyncSession
    ) -> str:
        """Build a short personalization note from the user's known weak
        topics, so the tutor can favor simpler explanations/examples for
        areas the student has struggled with. Returns "" if there is no
        weak-topic data yet (e.g. no quizzes attempted).
        """
        try:
            weak_topics = await self.progress_service.get_top_weak_topics(
                user_id=user_id, db=db, syllabus_id=syllabus_id, limit=3
            )
        except Exception as e:
            logger.warning(f"Could not load weak topics for user {user_id}: {e}")
            return ""

        if not weak_topics:
            return ""

        topic_list = ", ".join(
            f"{wt.topic_name} ({wt.accuracy:.0f}% accuracy)" for wt in weak_topics
        )
        return (
            "This student has previously struggled with these topics: "
            f"{topic_list}. Where relevant to their question, favor simpler "
            "explanations, more examples, and gentle connections back to "
            "these areas - but don't force it if the question is unrelated."
        )

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

        context = ""
        if syllabus_id:
            owned = await self._verify_syllabus_ownership(db, syllabus_id, user_id)
            if not owned:
                logger.warning(
                    f"User {user_id} requested syllabus {syllabus_id} they do not "
                    "own; ignoring syllabus_id for retrieval"
                )
            else:
                collection_name = self.vector_service.collection_name_for_syllabus(syllabus_id)
                context_docs = self.vector_service.retrieve_context(
                    collection_name,
                    message,
                    filter={
                        "$and": [
                            {"user_id": user_id},
                            {"syllabus_id": syllabus_id},
                        ]
                    },
                )
                context = self.vector_service.format_context(context_docs)

        personalization = await self._build_personalization_note(user_id, syllabus_id, db)

        system_parts = [
            "You are a helpful AI tutor."
        ]
        if context:
            system_parts.append(
                "Answer primarily using the retrieved material below. If the "
                "retrieved material does not contain the answer, say so before "
                f"using general knowledge.\n\n{context}"
            )
        if personalization:
            system_parts.append(personalization)

        if len(system_parts) > 1:
            messages = [{"role": "system", "content": "\n\n".join(system_parts)}] + messages

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