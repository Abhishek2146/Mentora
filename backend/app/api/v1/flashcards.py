"""
Flashcards API endpoints
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.flashcard import FlashcardDeck, Flashcard
from app.models.syllabus import Syllabus
from app.schemas.flashcard import FlashcardDeckCreate, FlashcardDeckOut, FlashcardOut
from app.services.flashcard_service import FlashcardService

router = APIRouter()
flashcard_service = FlashcardService()


class GenerateFlashcardsRequest(BaseModel):
    topic: Optional[str] = None
    syllabus_id: Optional[int] = None
    unit: Optional[str] = None
    count: int = Field(10, ge=1, le=30)
    student_level: str = "Bachelor"


class RatingRequest(BaseModel):
    rating: str  # "Again" | "Hard" | "Good" | "Easy"

    @property
    def score(self) -> int:
        return {"again": 1, "hard": 3, "good": 4, "easy": 5}.get(
            self.rating.strip().lower(), 4
        )


@router.post("/", response_model=FlashcardDeckOut, status_code=status.HTTP_201_CREATED)
async def create_deck(
    deck_data: FlashcardDeckCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    deck = FlashcardDeck(user_id=user_id, **deck_data.dict())
    db.add(deck)
    await db.commit()
    await db.refresh(deck)
    return deck


@router.get("/", response_model=List[FlashcardDeckOut])
async def list_decks(
    syllabus_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = select(FlashcardDeck).where(FlashcardDeck.user_id == user_id)
    if syllabus_id:
        query = query.where(FlashcardDeck.syllabus_id == syllabus_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{deck_id}", response_model=FlashcardDeckOut)
async def get_deck(
    deck_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(FlashcardDeck).where(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user_id)
    )
    deck = result.scalars().first()
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard deck not found")
    return deck


@router.get("/{deck_id}/due", response_model=List[FlashcardOut])
async def get_due_flashcards(
    deck_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await flashcard_service.get_due_flashcards(deck_id, db)


@router.get("/review/all", response_model=List[FlashcardOut])
async def get_review_cards(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Due flashcards across all of the user's decks, for the study page."""
    now = datetime.utcnow().isoformat()
    result = await db.execute(
        select(Flashcard)
        .join(FlashcardDeck, Flashcard.deck_id == FlashcardDeck.id)
        .where(
            FlashcardDeck.user_id == user_id,
            or_(
                Flashcard.next_review.is_(None),
                Flashcard.next_review <= now,
            ),
        )
        .limit(50)
    )
    return result.scalars().all()


@router.post("/generate", response_model=FlashcardDeckOut, status_code=status.HTTP_201_CREATED)
async def generate_flashcards(
    req: GenerateFlashcardsRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Generate an AI flashcard deck from the student's syllabus/RAG content.

    If no syllabus_id is given, the syllabus actually containing the topic
    is resolved automatically from the user's uploaded syllabi.
    """
    syllabus_id = req.syllabus_id
    topics = [req.topic] if req.topic else []

    if not syllabus_id:
        candidates = await db.execute(
            select(Syllabus).where(Syllabus.user_id == user_id).order_by(Syllabus.id.desc())
        )
        for syllabus in candidates.scalars().all():
            if _syllabus_contains_topic(syllabus.parsed_data, req.topic):
                syllabus_id = syllabus.id
                topics = [req.topic]
                break
        else:
            latest = await db.execute(
                select(Syllabus)
                .where(Syllabus.user_id == user_id)
                .order_by(Syllabus.id.desc())
                .limit(1)
            )
            syllabus = latest.scalars().first()
            if not syllabus:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Upload a syllabus first to generate flashcards.",
                )
            syllabus_id = syllabus.id

    try:
        return await flashcard_service.generate_flashcards(
            user_id=user_id,
            syllabus_id=syllabus_id,
            num_cards=req.count,
            db=db,
            unit=req.unit or "",
            topics=topics,
            student_level=req.student_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def _syllabus_contains_topic(parsed_data: Optional[dict], topic: Optional[str]) -> bool:
    """Best-effort check whether a topic appears in the parsed syllabus."""
    if not topic or not isinstance(parsed_data, dict):
        return False
    needle = topic.strip().lower()

    def _matches(value: str) -> bool:
        return needle and needle in str(value).strip().lower()

    for subject in (parsed_data.get("subjects") or []):
        if not isinstance(subject, dict):
            continue
        if _matches(subject.get("name") or ""):
            return True
        for chapter in (subject.get("chapters") or []):
            if not isinstance(chapter, dict):
                continue
            if _matches(chapter.get("name") or ""):
                return True
            for t in (chapter.get("topics") or []):
                if _matches(t):
                    return True
    return False


@router.post("/{card_id}/rating", response_model=FlashcardOut)
async def rate_flashcard(
    card_id: int,
    body: RatingRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Submit a spaced-repetition rating (Again/Hard/Good/Easy) for a card."""
    result = await db.execute(
        select(Flashcard)
        .join(FlashcardDeck, Flashcard.deck_id == FlashcardDeck.id)
        .where(Flashcard.id == card_id, FlashcardDeck.user_id == user_id)
    )
    card = result.scalars().first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")

    flashcard_service.update_flashcard_schedule(card, body.score)
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card
