# """
# Flashcard model
# """
# from sqlalchemy import Column, String, Text, ForeignKey, Integer
# from sqlalchemy.orm import relationship
# from app.database.base import BaseModel


# class FlashcardDeck(BaseModel):
#     __tablename__ = "flashcard_decks"

#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     title = Column(String(255), nullable=False)
#     description = Column(Text, nullable=True)
#     syllabus_id = Column(Integer, ForeignKey("syllabuses.id"), nullable=True)
#     subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
#     chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
#     is_ai_generated = Column(Boolean, default=False, nullable=False)

#     user = relationship("User", backref="flashcard_decks")
#     flashcards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")

#     class Config:
#         from_attributes = True


# class Flashcard(BaseModel):
#     __tablename__ = "flashcards"

#     deck_id = Column(Integer, ForeignKey("flashcard_decks.id", ondelete="CASCADE"), nullable=False)
#     front = Column(Text, nullable=False)
#     back = Column(Text, nullable=False)
#     difficulty = Column(String(20), default="unknown", nullable=False)
#     ease_factor = Column(Integer, default=250, nullable=False)
#     interval = Column(Integer, default=1, nullable=False)
#     repetitions = Column(Integer, default=0, nullable=False)
#     next_review = Column(String(50), nullable=True)
#     last_reviewed = Column(String(50), nullable=True)

#     deck = relationship("FlashcardDeck", back_populates="flashcards")

#     class Config:
#         from_attributes = True


"""
Flashcard model
"""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship, backref

from app.database.base import BaseModel


# ============================================================
# Flashcard Deck Model
# ============================================================

class FlashcardDeck(BaseModel):
    __tablename__ = "flashcard_decks"

    # --------------------------------------------------------
    # Columns
    # --------------------------------------------------------

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    syllabus_id = Column(
        Integer,
        ForeignKey("syllabuses.id"),
        nullable=True,
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=True,
    )

    chapter_id = Column(
        Integer,
        ForeignKey("chapters.id"),
        nullable=True,
    )

    is_ai_generated = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # --------------------------------------------------------
    # Relationships
    # --------------------------------------------------------

    user = relationship(
        "User",
        backref=backref("flashcard_decks", passive_deletes=True),
    )

    flashcards = relationship(
        "Flashcard",
        back_populates="deck",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# ============================================================
# Flashcard Model
# ============================================================

class Flashcard(BaseModel):
    __tablename__ = "flashcards"

    # --------------------------------------------------------
    # Columns
    # --------------------------------------------------------

    deck_id = Column(
        Integer,
        ForeignKey(
            "flashcard_decks.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    front = Column(
        Text,
        nullable=False,
    )

    back = Column(
        Text,
        nullable=False,
    )

    difficulty = Column(
        String(20),
        default="unknown",
        nullable=False,
    )

    # Stored as integer to represent the ease factor.
    # Example: 250 represents 2.50.
    ease_factor = Column(
        Integer,
        default=250,
        nullable=False,
    )

    interval = Column(
        Integer,
        default=1,
        nullable=False,
    )

    repetitions = Column(
        Integer,
        default=0,
        nullable=False,
    )

    next_review = Column(
        String(50),
        nullable=True,
    )

    last_reviewed = Column(
        String(50),
        nullable=True,
    )

    # --------------------------------------------------------
    # Relationships
    # --------------------------------------------------------

    deck = relationship(
        "FlashcardDeck",
        back_populates="flashcards",
    )


