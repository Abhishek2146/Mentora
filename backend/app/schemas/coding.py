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
    tags: Optional[List[str]] = None
    starter_code: Optional[str] = None
    test_cases: Optional[List[Any]] = None
    constraints: Optional[str] = None


class CodingProblemCreate(CodingProblemBase):
    pass


class CodingProblemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    starter_code: Optional[str] = None
    test_cases: Optional[List[Any]] = None
    constraints: Optional[str] = None


class CodingProblemOut(CodingProblemBase):
    id: int
    user_id: Optional[int] = None

    class Config:
        from_attributes = True

class CodingSubmissionBase(BaseModel):
    problem_id: int
    code: str
    language: str = Field(..., max_length=50)
    status: str = "pending"
    output: Optional[str] = None
    score: int = 0
    passed_test_cases: int = 0
    total_test_cases: int = 0
    execution_time: Optional[int] = None
    error_message: Optional[str] = None


class CodingSubmissionCreate(BaseModel):
    problem_id: int
    code: str
    language: str


class CodingSubmissionOut(CodingSubmissionBase):
    id: int
    user_id: int
    # NOTE: separate known issue, not fixed here - `submission.problem` is
    # an ORM relationship object, not a dict, and reading it inside an
    # async session without eager loading will fail. Left as-is since
    # it's outside the scope of the passed/memory_used column fix.
    problem: Optional[dict] = None

    class Config:
        from_attributes = True
