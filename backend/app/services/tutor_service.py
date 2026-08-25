"""
Tutor (AI Chatbot) Service
"""
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
            if session is None:
                session = ChatSession(
                    user_id=user_id,
                    title=message[:50] + "..." if len(message) > 50 else message,
                    syllabus_id=syllabus_id,
                )
                db.add(session)
                await db.commit()
                await db.refresh(session)
        else:
            session = ChatSession(
                user_id=user_id,
                title=message[:50] + "..." if len(message) > 50 else message,
                syllabus_id=syllabus_id,
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

        # Load prior conversation history so the tutor has context for
        # follow-up questions (e.g. "explain that again", "what about chapter 3?").
        history_result = await db.execute(
            select(ChatMessage).where(
                ChatMessage.session_id == session.id
            ).order_by(ChatMessage.sequence)
        )
        existing_messages: List[ChatMessage] = history_result.scalars().all()
        next_sequence = len(existing_messages) + 1

        history: List[Dict[str, str]] = []
        for msg in existing_messages:
            history.append({"role": msg.role, "content": msg.content})

        messages: List[Dict[str, str]] = []

        context = ""
        if syllabus_id:
            logger.debug(
                "[Tutor] syllabus_id=%s, user_id=%s, query=%r",
                syllabus_id,
                user_id,
                message[:100],
            )
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

                logger.debug(
                    "[Tutor] Retrieved %d documents from collection '%s'; "
                    "context length=%d chars; context preview=%s",
                    len(context_docs),
                    collection_name,
                    len(context),
                    context[:500] if context else "(empty)",
                )
                for i, doc in enumerate(context_docs):
                    logger.debug(
                        "[Tutor] Doc %d: metadata=%s, content_len=%d, "
                        "preview=%s",
                        i,
                        doc.metadata,
                        len(doc.page_content),
                        doc.page_content[:200],
                    )

        personalization = await self._build_personalization_note(user_id, syllabus_id, db)

        system_parts = [
            "You are a helpful AI tutor.",
            (
                "Format your reply as clean plain text for a chat interface. "
                "Use short paragraphs and simple bullet lists starting with a "
                "dash (-). Do NOT use Markdown formatting (no **, *, |, ---, "
                "#, >), do NOT use HTML tags (no <br> or similar), and do not "
                "use tables."
            ),
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
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        messages.extend(history)
        messages.append({"role": "user", "content": message})

        ai_response = await self.llm_service.chat_completion(messages, temperature=0.7)

        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=message,
            sequence=next_sequence,
        )
        db.add(user_msg)

        ai_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=ai_response,
            sequence=next_sequence + 1,
        )
        db.add(ai_msg)

        await db.commit()

        return {"response": ai_response, "session_id": session.id}