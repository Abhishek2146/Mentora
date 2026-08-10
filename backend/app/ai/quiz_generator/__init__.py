"""
Quiz Generator module
"""
from app.services.quiz_service import QuizService

quiz_generator = QuizService()

__all__ = ["quiz_generator", "QuizService"]
