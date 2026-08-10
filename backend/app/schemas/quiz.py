"""
Quiz schemas
"""
from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    CODE = "code"


class QuestionBase(BaseModel):
    question_type: QuestionType = QuestionType.MCQ
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: str = Field("medium", max_length=20)
    order: int = 0


class QuestionCreate(QuestionBase):
    pass


class QuestionOut(QuestionBase):
    id: int

    class Config:
        from_attributes = True


class QuizBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    syllabus_id: Optional[int] = None
    subject_id: Optional[int] = None
    chapter_id: Optional[int] = None
    num_questions: int = 10
    time_limit: Optional[int] = None
    is_active: bool = True


class QuizCreate(QuizBase):
    pass


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    num_questions: Optional[int] = None
    time_limit: Optional[int] = None
    is_active: Optional[bool] = None


class QuizOut(QuizBase):
    id: int
    questions: List[QuestionOut] = []

    class Config:
        from_attributes = True


class QuizAttemptBase(BaseModel):
    quiz_id: int
    score: int
    total_questions: int
    correct_answers: int
    time_taken: Optional[int] = None
    answers: Optional[Any] = None
    is_passed: bool = False


class QuizAttemptCreate(QuizAttemptBase):
    pass


class QuizAttemptOut(QuizAttemptBase):
    id: int
    user_id: int
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
