"""
Flashcard Service
"""
import asyncio
from typing import List, Optional, Union, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logger import get_logger
from app.models.syllabus import Syllabus
from app.models.flashcard import FlashcardDeck, Flashcard
from app.services.llm_service import LLMService
from app.services.progress_service import ProgressService

logger = get_logger(__name__)


class FlashcardService:
    def __init__(self):
        self.llm_service = LLMService()
        self.progress_service = ProgressService()
        self._vector_service = None

    @property
    def vector_service(self):
        """Lazily create the VectorService so flashcards still work when
        ChromaDB is unavailable."""
        if self._vector_service is None:
            from app.services.vector_service import VectorService
            self._vector_service = VectorService()
        return self._vector_service

    async def generate_flashcards(
        self,
        user_id: int,
        syllabus_id: int,
        content: Optional[str] = None,
        num_cards: int = 10,
        db: Optional[AsyncSession] = None,
        subject: str = "",
        unit: str = "",
        topics: Optional[List[str]] = None,
        student_level: str = "Bachelor",
    ) -> Union[FlashcardDeck, List[dict]]:
        """Generate exam-oriented flashcards from syllabus/RAG content.

        The Flashcard Generation Engine prompt in LLMService enforces the
        card types, difficulty distribution and RAG-only grounding; this
        method resolves the source content and persists the deck.
        """
        weak_topics: List[str] = []
        previous_questions: List[str] = []
        if db:
            syllabus_result = await db.execute(
                select(Syllabus).where(Syllabus.id == syllabus_id, Syllabus.user_id == user_id)
            )
            syllabus = syllabus_result.scalars().first()
            if not syllabus:
                raise ValueError("Syllabus not found")

            if not subject:
                subject = syllabus.title or ""

            # RAG-retrieved content scoped to this syllabus is the primary
            # source of truth; fall back to raw extracted text.
            if not content:
                query_text = ", ".join(topics) if topics else (subject or "syllabus topics")
                try:
                    content = await asyncio.to_thread(
                        self.vector_service.retrieve_scoped_content,
                        syllabus_id, user_id, query_text,
                    )
                except Exception as e:
                    logger.warning("RAG retrieval failed for flashcards: %s", e)
                    content = ""
            if not content and syllabus.extracted_text:
                content = syllabus.extracted_text[: settings.LLM_MAX_INPUT_CHARS]

            try:
                wt = await self.progress_service.get_top_weak_topics(
                    user_id=user_id, db=db, syllabus_id=syllabus_id, limit=3
                )
                weak_topics = [w.topic_name for w in wt]
            except Exception as e:
                logger.warning("Weak-topic lookup failed for flashcards: %s", e)

            # Feed existing questions to the engine so regenerated decks
            # don't repeat cards the student already has.
            try:
                prev_result = await db.execute(
                    select(Flashcard.front)
                    .join(FlashcardDeck, Flashcard.deck_id == FlashcardDeck.id)
                    .where(FlashcardDeck.user_id == user_id)
                    .order_by(Flashcard.id.desc())
                    .limit(80)
                )
                previous_questions = [row[0] for row in prev_result.all() if row[0]]
            except Exception as e:
                logger.warning("Previous-question lookup failed: %s", e)
                previous_questions = []

        engine_result = await self.llm_service.generate_flashcards(
            retrieved_content=content or "",
            subject=subject,
            unit=unit,
            topics=topics,
            student_level=student_level,
            weak_topics=weak_topics,
            num_cards=num_cards,
            previous_questions=previous_questions,
        )
        flashcards_data = engine_result.get("flashcards", [])

        if not flashcards_data:
            if not content:
                raise ValueError(
                    "No study content was found for this syllabus/topic. "
                    "Re-upload the syllabus (PDF/text works best) or pick a "
                    "topic that exists in it, then try again."
                )
            raise ValueError(
                "The AI could not generate flashcards from this content. "
                "Try a different topic or try again in a moment."
            )

        if db:
            deck_title = (
                f"AI Generated - {topics[0]}" if topics and len(topics) == 1
                else f"AI Generated - {unit}" if unit
                else f"AI Generated - {subject or syllabus.title}"
            )
            deck = FlashcardDeck(
                user_id=user_id,
                title=deck_title[:255],
                description=engine_result.get("topic") or unit or None,
                syllabus_id=syllabus_id,
                is_ai_generated=True,
            )
            db.add(deck)
            await db.commit()
            await db.refresh(deck)

            for card_data in flashcards_data:
                db.add(
                    Flashcard(
                        deck_id=deck.id,
                        front=card_data.get("question", ""),
                        back=card_data.get("answer", ""),
                        difficulty=str(card_data.get("difficulty", "unknown")).capitalize(),
                    )
                )

            await db.commit()
            # Reload so the response includes the newly created cards.
            await db.refresh(deck)
            return deck
        else:
            return flashcards_data

    async def get_due_flashcards(self, deck_id: int, db: AsyncSession) -> List[Flashcard]:
        """Get flashcards that are due for review."""
        from datetime import datetime
        from sqlalchemy import or_
        now = datetime.utcnow().isoformat()
        result = await db.execute(
            select(Flashcard).where(
                Flashcard.deck_id == deck_id,
                or_(
                    Flashcard.next_review.is_(None),
                    Flashcard.next_review <= now,
                ),
            )
        )
        return result.scalars().all()

    def update_flashcard_schedule(
        self,
        flashcard: Flashcard,
        rating: int,
    ) -> None:
        """Update flashcard based on spaced repetition rating."""
        if not 0 <= rating <= 5:
            raise ValueError("rating must be between 0 and 5")

        ease = max(1.3, (flashcard.ease_factor or 250) / 100.0)
        ease += (rating - 3) * 0.1
        ease = max(1.3, ease)

        if rating < 3:
            repetitions = 0
            interval = 1
        else:
            repetitions = flashcard.repetitions + 1
            if repetitions == 1:
                interval = 1
            elif repetitions == 2:
                interval = 6
            else:
                interval = max(1, round(flashcard.interval * ease))

        flashcard.ease_factor = round(ease * 100)
        flashcard.repetitions = repetitions
        flashcard.interval = interval

        from datetime import datetime, timedelta
        now = datetime.utcnow()
        flashcard.next_review = (now + timedelta(days=interval)).isoformat()
        flashcard.last_reviewed = now.isoformat()
