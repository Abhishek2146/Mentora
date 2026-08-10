"""
Flashcard Generator module
"""
from app.services.flashcard_service import FlashcardService

flashcard_generator = FlashcardService()

__all__ = ["flashcard_generator", "FlashcardService"]
