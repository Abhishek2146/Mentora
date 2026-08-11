# """
# Coding problem models
# """
# from enum import Enum
# from sqlalchemy import Column, String, Text, ForeignKey, Integer, JSON, Boolean
# from sqlalchemy.orm import relationship
# from app.database.base import BaseModel


# class Difficulty(str, Enum):
#     EASY = "easy"
#     MEDIUM = "medium"
#     HARD = "hard"


# class CodingProblem(BaseModel):
#     __tablename__ = "coding_problems"

#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
#     title = Column(String(255), nullable=False)
#     description = Column(Text, nullable=False)
#     difficulty = Column(String(20), default=Difficulty.MEDIUM.value, nullable=False)
#     category = Column(String(100), nullable=True)
#     tags = Column(JSON, nullable=True)
#     starter_code = Column(Text, nullable=True)
#     solution = Column(Text, nullable=True)
#     test_cases = Column(JSON, nullable=True)
#     constraints = Column(Text, nullable=True)

#     user = relationship("User", backref="coding_problems")
#     submissions = relationship("CodingSubmission", back_populates="problem", cascade="all, delete-orphan")

#     class Config:
#         from_attributes = True


# class CodingSubmission(BaseModel):
#     __tablename__ = "coding_submissions"

#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     problem_id = Column(Integer, ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False)
#     code = Column(Text, nullable=False)
#     language = Column(String(50), nullable=False)
#     status = Column(String(20), default="pending", nullable=False)
#     output = Column(Text, nullable=True)
#     passed = Column(Boolean, default=False, nullable=False)
#     execution_time = Column(Integer, nullable=True)
#     memory_used = Column(Integer, nullable=True)

#     user = relationship("User", backref="coding_submissions")
#     problem = relationship("CodingProblem", back_populates="submissions")

#     class Config:
#         from_attributes = True


"""
Coding Problem models
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    ForeignKey,
    Integer,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship

from app.database.base import BaseModel


class CodingProblem(BaseModel):
    __tablename__ = "coding_problems"

    # Problem ownership / academic mapping
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
    )

    chapter_id = Column(
        Integer,
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Problem information
    title = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=False,
    )

    difficulty = Column(
        String(20),
        default="medium",
        nullable=False,
    )

    category = Column(
        String(100),
        nullable=True,
    )

    # Programming language
    language = Column(
        String(50),
        default="python",
        nullable=False,
    )

    # Coding information
    starter_code = Column(
        Text,
        nullable=True,
    )

    solution_code = Column(
        Text,
        nullable=True,
    )

    input_format = Column(
        Text,
        nullable=True,
    )

    output_format = Column(
        Text,
        nullable=True,
    )

    constraints = Column(
        Text,
        nullable=True,
    )

    examples = Column(
        JSON,
        nullable=True,
    )

    test_cases = Column(
        JSON,
        nullable=True,
    )

    hints = Column(
        JSON,
        nullable=True,
    )

    tags = Column(
        JSON,
        nullable=True,
    )

    # AI information
    is_ai_generated = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    ai_explanation = Column(
        Text,
        nullable=True,
    )

    # Status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    user = relationship(
        "User",
        backref="coding_problems",
    )

    subject = relationship(
        "Subject",
        backref="coding_problems",
    )

    chapter = relationship(
        "Chapter",
        backref="coding_problems",
    )

    submissions = relationship(
        "CodingSubmission",
        back_populates="problem",
        cascade="all, delete-orphan",
    )


class CodingSubmission(BaseModel):
    """
    Stores a user's submission for a coding problem.
    """

    __tablename__ = "coding_submissions"

    problem_id = Column(
        Integer,
        ForeignKey("coding_problems.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Submitted code
    code = Column(
        Text,
        nullable=False,
    )

    language = Column(
        String(50),
        default="python",
        nullable=False,
    )

    # Execution/result information
    status = Column(
        String(30),
        default="pending",
        nullable=False,
    )

    score = Column(
        Integer,
        default=0,
        nullable=False,
    )

    passed_test_cases = Column(
        Integer,
        default=0,
        nullable=False,
    )

    total_test_cases = Column(
        Integer,
        default=0,
        nullable=False,
    )

    execution_time = Column(
        Integer,
        nullable=True,
    )

    error_message = Column(
        Text,
        nullable=True,
    )

    output = Column(
        Text,
        nullable=True,
    )

    # Relationships
    problem = relationship(
        "CodingProblem",
        back_populates="submissions",
    )

    user = relationship(
        "User",
        backref="coding_submissions",
    )

