"""
Coding schemas
"""
from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CodingProblemBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    difficulty: Difficulty = Difficulty.MEDIUM
    category: Optional[str] = None
    language: str = "python"
    tags: Optional[List[str]] = None
    starter_code: Optional[str] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    examples: Optional[List[Any]] = None
    test_cases: Optional[List[Any]] = None
    hints: Optional[List[str]] = None
    constraints: Optional[str] = None


class CodingProblemCreate(CodingProblemBase):
    pass


class CodingProblemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    category: Optional[str] = None
    language: Optional[str] = None
    tags: Optional[List[str]] = None
    starter_code: Optional[str] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    examples: Optional[List[Any]] = None
    test_cases: Optional[List[Any]] = None
    hints: Optional[List[str]] = None
    constraints: Optional[str] = None


class CodingProblemOut(CodingProblemBase):
    id: int
    user_id: Optional[int] = None
    is_ai_generated: bool = False

    class Config:
        from_attributes = True


class GenerateCodingProblemRequest(BaseModel):
    topic: Optional[str] = None
    syllabus_id: Optional[int] = None
    difficulty: Difficulty = Difficulty.MEDIUM
    language: str = Field("python", max_length=50)


class CodingSubmitBody(BaseModel):
    code: str
    language: str = Field(..., max_length=50)


class CodingSubmissionCreate(BaseModel):
    problem_id: int
    code: str
    language: str


class CodingSubmissionOut(BaseModel):
    id: int
    user_id: int
    problem_id: int
    code: str
    language: str
    status: str
    output: Optional[str] = None
    score: int = 0
    passed_test_cases: int = 0
    total_test_cases: int = 0
    execution_time: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
