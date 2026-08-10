"""
Coding problem models
"""
from enum import Enum
from sqlalchemy import Column, String, Text, ForeignKey, Integer, JSON, Boolean
from sqlalchemy.orm import relationship
from app.database.base import BaseModel


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CodingProblem(BaseModel):
    __tablename__ = "coding_problems"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    difficulty = Column(String(20), default=Difficulty.MEDIUM.value, nullable=False)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)
    starter_code = Column(Text, nullable=True)
    solution = Column(Text, nullable=True)
    test_cases = Column(JSON, nullable=True)
    constraints = Column(Text, nullable=True)

    user = relationship("User", backref="coding_problems")
    submissions = relationship("CodingSubmission", back_populates="problem", cascade="all, delete-orphan")

    class Config:
        from_attributes = True


class CodingSubmission(BaseModel):
    __tablename__ = "coding_submissions"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id = Column(Integer, ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False)
    code = Column(Text, nullable=False)
    language = Column(String(50), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    output = Column(Text, nullable=True)
    passed = Column(Boolean, default=False, nullable=False)
    execution_time = Column(Integer, nullable=True)
    memory_used = Column(Integer, nullable=True)

    user = relationship("User", backref="coding_submissions")
    problem = relationship("CodingProblem", back_populates="submissions")

    class Config:
        from_attributes = True
