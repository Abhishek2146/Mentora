"""
Flashcard Service
"""
from typing import List, Optional

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
    ) -> FlashcardDeck:
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
        result = await db.execute(
            select(Flashcard).where(
                Flashcard.deck_id == deck_id,
                (Flashcard.next_review == None) | (Flashcard.next_review <= datetime.utcnow().isoformat()),
            )
        )
        return result.scalars().all()

    def update_flashcard_schedule(
        self,
        flashcard: Flashcard,
        rating: int,
    ) -> None:
        """Update flashcard based on spaced repetition rating."""
        ease_factor = max(1.3, flashcard.ease_factor + (rating - 3) * (0.1 * flashcard.ease_factor))
        if rating < 3:
            repetitions = 0
            interval = 1
        else:
            repetitions = flashcard.repetitions + 1
            interval = max(1, int(flashcard.interval * ease_factor / 100))

        flashcard.ease_factor = int(ease_factor * 100)
        flashcard.repetitions = repetitions
        flashcard.interval = interval
        from datetime import datetime, timedelta
        flashcard.next_review = (datetime.utcnow() + timedelta(days=interval)).isoformat()
        flashcard.last_reviewed = datetime.utcnow().isoformat()
