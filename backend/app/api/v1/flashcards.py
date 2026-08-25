"""
Flashcards API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.flashcard import FlashcardDeck, Flashcard
from app.schemas.flashcard import FlashcardDeckCreate, FlashcardDeckOut, FlashcardOut
from app.services.flashcard_service import FlashcardService

router = APIRouter()
flashcard_service = FlashcardService()


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

    result = await db.execute(
        select(FlashcardDeck)
        .options(selectinload(FlashcardDeck.flashcards))
        .where(FlashcardDeck.id == deck.id)
    )
    return result.scalars().first()


@router.get("/", response_model=List[FlashcardDeckOut])
async def list_decks(
    syllabus_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = (
        select(FlashcardDeck)
        .options(selectinload(FlashcardDeck.flashcards))
        .where(FlashcardDeck.user_id == user_id)
    )
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
        select(FlashcardDeck)
        .options(selectinload(FlashcardDeck.flashcards))
        .where(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user_id)
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
    deck_result = await db.execute(
        select(FlashcardDeck).where(
            FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user_id
        )
    )
    if not deck_result.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard deck not found")

    return await flashcard_service.get_due_flashcards(deck_id, db)


@router.post("/{deck_id}/flashcards/{flashcard_id}/review", response_model=FlashcardOut)
async def review_flashcard(
    deck_id: int,
    flashcard_id: int,
    rating: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Record a spaced-repetition review (rating 0-5) for a flashcard."""
    deck_result = await db.execute(
        select(FlashcardDeck).where(
            FlashcardDeck.id == deck_id, FlashcardDeck.user_id == user_id
        )
    )
    if not deck_result.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard deck not found")

    card_result = await db.execute(
        select(Flashcard).where(
            Flashcard.id == flashcard_id, Flashcard.deck_id == deck_id
        )
    )
    flashcard = card_result.scalars().first()
    if not flashcard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")

    try:
        flashcard_service.update_flashcard_schedule(flashcard, rating)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    db.add(flashcard)
    await db.commit()
    await db.refresh(flashcard)
    return flashcard
