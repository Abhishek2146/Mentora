"""
Quiz models
"""
from enum import Enum
from sqlalchemy import Column, String, Text, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from app.database.base import BaseModel


class QuestionType(str, Enum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    CODE = "code"


class Quiz(BaseModel):
    __tablename__ = "quizzes"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    syllabus_id = Column(Integer, ForeignKey("syllabuses.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
    num_questions = Column(Integer, default=10, nullable=False)
    time_limit = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_ai_generated = Column(Boolean, default=False, nullable=False)

    user = relationship("User", backref="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")

    class Config:
        from_attributes = True


class Question(BaseModel):
    __tablename__ = "questions"

    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_type = Column(String(20), default=QuestionType.MCQ.value, nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)
    correct_answer = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=True)
    difficulty = Column(String(20), default="medium", nullable=False)
    order = Column(Integer, default=0, nullable=False)

    quiz = relationship("Quiz", back_populates="questions")

    class Config:
        from_attributes = True


class QuizAttempt(BaseModel):
    __tablename__ = "quiz_attempts"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    time_taken = Column(Integer, nullable=True)
    answers = Column(JSON, nullable=True)
    is_passed = Column(Boolean, default=False, nullable=False)

    user = relationship("User", backref="quiz_attempts")
    quiz = relationship("Quiz", back_populates="attempts")

    class Config:
        from_attributes = True
