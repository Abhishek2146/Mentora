"""
Flashcard Service
"""
from typing import List, Optional, Union, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logger import get_logger
from app.models.syllabus import Syllabus
from app.models.flashcard import FlashcardDeck, Flashcard
from app.services.llm_service import LLMService

logger = get_logger(__name__)


class FlashcardService:
    def __init__(self):
        self.llm_service = LLMService()

    async def generate_flashcards(
        self,
        user_id: int,
        syllabus_id: int,
        content: str,
        num_cards: int = 20,
        db: Optional[AsyncSession] = None,
    ) -> Union[FlashcardDeck, List[dict]]:
        """Generate flashcards from syllabus content."""
        flashcards_data = await self.llm_service.generate_flashcards(content, num_cards)

        if db:
            syllabus_result = await db.execute(
                select(Syllabus).where(Syllabus.id == syllabus_id, Syllabus.user_id == user_id)
            )
            syllabus = syllabus_result.scalars().first()
            if not syllabus:
                raise ValueError("Syllabus not found")

            deck = FlashcardDeck(
                user_id=user_id,
                title=f"AI Generated - {syllabus.title}",
                syllabus_id=syllabus_id,
                is_ai_generated=True,
            )
            await db.commit()
            await db.refresh(deck)

            for i, card_data in enumerate(flashcards_data):
                card = Flashcard(
                    deck_id=deck.id,
                    front=card_data.get("front", ""),
                    back=card_data.get("back", ""),
                )
                db.add(card)

            await db.commit()
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
