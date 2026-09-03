"""
Tutor (AI Chatbot) Service
"""
import re
from typing import Optional, List, Dict, Any
from sqlalchemy import func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logger import get_logger
from app.models.chat_history import ChatSession, ChatMessage
from app.models.syllabus import Syllabus
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService
from app.services.progress_service import ProgressService
from app.services.syllabus_structure import (
    TUTOR_NOT_FOUND_MESSAGE,
    build_tutor_system_prompt,
)

logger = get_logger(__name__)


class TutorService:
    def __init__(self):
        self.llm_service = LLMService()
        self.vector_service = VectorService()
        self.progress_service = ProgressService()

    async def _verify_syllabus_ownership(
        self, db: AsyncSession, syllabus_id: int, user_id: int
    ) -> Optional[Syllabus]:
        """Return the syllabus row when it belongs to the authenticated
        user, else None. Guards RAG retrieval so a tutor session can only
        ever pull vectors from an owner-scoped collection."""
        result = await db.execute(
            select(Syllabus).where(
                Syllabus.id == syllabus_id, Syllabus.user_id == user_id
            )
        )
        return result.scalars().first()

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

    @staticmethod
    def _truncate_context(context: str, max_chars: int) -> str:
        """Truncate RAG context to fit within the character budget while
        preserving whole source blocks.  Sources are separated by double
        newlines and start with ``SOURCE N``.  We drop trailing partial
        blocks rather than cutting mid-sentence."""
        if len(context) <= max_chars:
            return context

        truncated = context[:max_chars]
        # Try to cut at the last complete source block boundary.
        last_boundary = truncated.rfind("\n\nSOURCE ")
        if last_boundary == -1:
            last_boundary = truncated.rfind("\n\n")
        if last_boundary > 0:
            truncated = truncated[:last_boundary]

        logger.info(
            "[Tutor] RAG context truncated from %d to %d chars "
            "(%d source blocks kept)",
            len(context),
            len(truncated),
            truncated.count("SOURCE "),
        )
        return truncated

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate using the configured chars-per-token ratio."""
        return len(text) // settings.TUTOR_CHARS_PER_TOKEN

    @staticmethod
    def _ensure_newlines(text: str) -> str:
        """Ensure numbered points each start on their own line.

        If the LLM returns points like:
            1. First. 2. Second. 3. Third.
        This converts them to:
            1. First.
            2. Second.
            3. Third.
        """
        # Insert newline before numbered items that follow text on the same line.
        # Matches patterns like ". 2." or ") 2." where a number follows without a newline.
        text = re.sub(r'(?<=\S)\s+(\d+)\.\s', r'\n\1. ', text)
        # Also handle cases where label lines run into next numbered item
        # e.g. "Key Points: 1. First" -> "Key Points:\n1. First"
        text = re.sub(r'(Key Points:|Important Points:|Advantages:|Limitations:|Differences:)\s+(\d+)\.\s', r'\1\n\2. ', text)
        return text

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
        all_messages: List[ChatMessage] = history_result.scalars().all()
          

        max_seq_result = await db.execute(
            select(sql_func.max(ChatMessage.sequence)).where(
                ChatMessage.session_id == session.id
            )
        )

        max_seq = max_seq_result.scalar_one_or_none()
        next_sequence = (max_seq or 0) + 1

        # ── Budget: keep only the most recent messages ──────────────
        max_history = settings.TUTOR_MAX_HISTORY_MESSAGES
        if len(all_messages) > max_history:
            all_messages = all_messages[-max_history:]
            logger.info(
                "[Tutor] Conversation history truncated to last %d messages "
                "(total was %d)",
                max_history,
                next_sequence - 1,
            )

        history: List[Dict[str, str]] = []
        for msg in all_messages:
            history.append({"role": msg.role, "content": msg.content})
               # Use the previous user question together with the current question
        # for retrieval. This helps follow-up questions such as
        # "Explain its types." retrieve the topic from the previous turn.
        retrieval_query = message

        prior_user_messages = [
            h["content"]
            for h in history
            if h["role"] == "user"
        ]

        if prior_user_messages:
            retrieval_query = (
                f"{prior_user_messages[-1]} {message}"
            )

        logger.info(
            f"TUTOR QUERY: {message!r} "
            f"syllabus_id={syllabus_id} "
            f"user_id={user_id} "
            f"history_messages={len(history)}"
        )

        # Detect broad overview queries that need more context than a
        # single-unit question.  These phrases typically require the
        # course-level overview document (all units + credit hours).
        _OVERVIEW_PATTERNS = (
            r"credit\s*hour",
            r"main\s+topic",
            r"all\s+topic",
            r"all\s+unit",
            r"list\s+(of\s+)?(topic|unit|chapter|subject)",
            r"topics?\s+covered",
            r"units?\s+covered",
            r"chapters?\s+covered",
            r"course\s+(topic|unit|chapter|content|overview|structure|outline|summary)",
            r"syllabus\s+(topic|unit|chapter|content|overview|structure|outline|summary)",
            r"what.*topic",
            r"what.*unit",
            r"what.*chapter",
            r"overview",
        )
        _msg_lower = message.lower()
        is_overview_query = any(
            re.search(pat, _msg_lower) for pat in _OVERVIEW_PATTERNS
        )
        # Overview queries get a higher k to pull in the course overview
        # document even when many per-unit chunks score higher.
        retrieval_k = settings.RAG_TOP_K * 3 if is_overview_query else settings.RAG_TOP_K
        if is_overview_query:
            logger.info(
                "[Tutor] Detected broad overview query; using retrieval_k=%d",
                retrieval_k,
            )

        context = ""
        context_docs = []
        syllabus: Optional[Syllabus] = None
        if syllabus_id:
            syllabus = await self._verify_syllabus_ownership(db, syllabus_id, user_id)
            if syllabus is None:
                logger.warning(
                    f"User {user_id} requested syllabus {syllabus_id} they do not "
                    "own; ignoring syllabus_id for retrieval"
                )
            else:
                collection_name = self.vector_service.collection_name_for_syllabus(syllabus_id)
                logger.info(
                    "[RETRIEVAL] tutor query for syllabus_id=%s: %r",
                    syllabus_id,
                    retrieval_query[:200],
                )
                context_docs = self.vector_service.retrieve_context(
                    collection_name,
                    retrieval_query,
                    k=retrieval_k,
                    filter={
                        "$and": [
                            {"user_id": user_id},
                            {"syllabus_id": syllabus_id},
                        ]
                    },
                )
            context = self.vector_service.format_context(context_docs)

        # Overview queries get a larger context budget so the full course
        # summary (all units + topics) fits within the system prompt.
        max_context_chars = (
            settings.TUTOR_MAX_CONTEXT_CHARS * 2
            if is_overview_query
            else settings.TUTOR_MAX_CONTEXT_CHARS
        )
        context = self._truncate_context(context, max_context_chars)

        logger.info(f"TUTOR CONTEXT: retrieved_docs={len(context_docs)} context_length={len(context)}")

        personalization = await self._build_personalization_note(user_id, syllabus_id, db)

        # ── Grounded fallback: never let the model improvise course
        # content.  When a syllabus is selected but retrieval found
        # nothing relevant, answer with the canned not-found message
        # instead of calling the LLM (STEP: no hallucinated units).
        if syllabus is not None and not context_docs:
            logger.info(
                "[Tutor] No relevant syllabus content retrieved; returning "
                "grounded not-found response without LLM call"
            )
            ai_response = TUTOR_NOT_FOUND_MESSAGE
        else:
            system_prompt = build_tutor_system_prompt(
                context=context,
                syllabus_selected=syllabus is not None,
                personalization=personalization,
                syllabus_title=(syllabus.title if syllabus else ""),
            )

            # Build the final LLM message sequence:
            #
            # SYSTEM → previous conversation → current user question
            #
            # Do not put the current question into messages before this point,
            # otherwise it would be duplicated.
            messages: List[Dict[str, str]] = [
                {"role": "system", "content": system_prompt},
            ]

            messages.extend(history)

            messages.append(
                {
                    "role": "user",
                    "content": message,
                }
            )

            # ── Diagnostics: log per-message request size ───────────────
            logger.info(
                "[Tutor] Request breakdown (%d messages):",
                len(messages),
            )
            est_tokens_total = 0
            for i, msg in enumerate(messages):
                chars = len(msg["content"])
                toks = self._estimate_tokens(msg["content"])
                est_tokens_total += toks
                logger.info(
                    "  [%d] role=%s chars=%d ~tokens=%d preview=%r",
                    i,
                    msg["role"],
                    chars,
                    toks,
                    msg["content"][:80],
                )
            logger.info(
                "[Tutor] Total: ~%d chars, ~%d tokens",
                sum(len(m["content"]) for m in messages),
                est_tokens_total,
            )

            try:
                ai_response = await self.llm_service.chat_completion(
                    messages, temperature=0.7
                )
            except Exception as exc:
                error_str = str(exc).lower()
                if "413" in error_str or "request entity too large" in error_str:
                    logger.error(
                        "[Tutor] Groq rejected request as too large "
                        "(~%d tokens). Retrying with minimal context.",
                        est_tokens_total,
                    )
                    # Keep the grounding rules but drop the bulky context.
                    minimal_system = build_tutor_system_prompt(
                        context="",
                        syllabus_selected=syllabus is not None,
                        personalization="",
                        syllabus_title=(syllabus.title if syllabus else ""),
                    )
                    reduced_messages = [
                        {"role": "system", "content": minimal_system},
                        messages[-1],  # user's latest question only
                    ]
                    logger.info(
                        "[Tutor] Retrying with minimal context: "
                        "~%d chars, ~%d tokens",
                        sum(len(m["content"]) for m in reduced_messages),
                        sum(
                            self._estimate_tokens(m["content"])
                            for m in reduced_messages
                        ),
                    )
                    ai_response = await self.llm_service.chat_completion(
                        reduced_messages, temperature=0.7
                    )
                else:
                    raise

        ai_response = self._ensure_newlines(ai_response)

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

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        return {"response": ai_response, "session_id": session.id}