# """
# Study Plan model
# """
# from sqlalchemy import Column, String, Text, ForeignKey, Integer, Date, JSON, Boolean
# from sqlalchemy.orm import relationship
# from app.database.base import BaseModel


# class StudyPlan(BaseModel):
#     __tablename__ = "study_plans"

#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     title = Column(String(255), nullable=False)
#     description = Column(Text, nullable=True)
#     start_date = Column(Date, nullable=False)
#     end_date = Column(Date, nullable=True)
#     syllabus_id = Column(Integer, ForeignKey("syllabuses.id"), nullable=True)
#     is_active = Column(Boolean, default=True, nullable=False)
#     plan_data = Column(JSON, nullable=True)

#     user = relationship("User", backref="study_plans")
#     syllabus = relationship("Syllabus", backref="study_plans")
#     tasks = relationship("StudyTask", back_populates="study_plan", cascade="all, delete-orphan")

#     class Config:
#         from_attributes = True


# class StudyTask(BaseModel):
#     __tablename__ = "study_tasks"

#     study_plan_id = Column(Integer, ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False)
#     title = Column(String(255), nullable=False)
#     description = Column(Text, nullable=True)
#     subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
#     chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
#     due_date = Column(Date, nullable=True)
#     completed = Column(Boolean, default=False, nullable=False)
#     task_type = Column(String(50), nullable=True)
#     metadata = Column(JSON, nullable=True)

#     study_plan = relationship("StudyPlan", back_populates="tasks")
#     subject = relationship("Subject", backref="study_tasks")
#     chapter = relationship("Chapter", backref="study_tasks")

#     class Config:
#         from_attributes = True


"""
Study Plan model
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    ForeignKey,
    Integer,
    Date,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship

from app.database.base import BaseModel


# ==================================================
# Study Plan Model
# ==================================================

class StudyPlan(BaseModel):
    __tablename__ = "study_plans"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
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

    start_date = Column(
        Date,
        nullable=False,
    )

    end_date = Column(
        Date,
        nullable=True,
    )

    syllabus_id = Column(
        Integer,
        ForeignKey("syllabuses.id"),
        nullable=True,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    plan_data = Column(
        JSON,
        nullable=True,
    )

    # Relationships
    user = relationship(
        "User",
        backref="study_plans",
    )

    syllabus = relationship(
        "Syllabus",
        backref="study_plans",
    )

    tasks = relationship(
        "StudyTask",
        back_populates="study_plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# ==================================================
# Study Task Model
# ==================================================

class StudyTask(BaseModel):
    __tablename__ = "study_tasks"

    study_plan_id = Column(
        Integer,
        ForeignKey(
            "study_plans.id",
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

    due_date = Column(
        Date,
        nullable=True,
    )

    completed = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    task_type = Column(
        String(50),
        nullable=True,
    )

    # "metadata" is reserved by SQLAlchemy,
    # so use "task_metadata" as the Python attribute
    # while keeping "metadata" as the database column.
    task_metadata = Column(
        "metadata",
        JSON,
        nullable=True,
    )

    # Relationships
    study_plan = relationship(
        "StudyPlan",
        back_populates="tasks",
    )

    subject = relationship(
        "Subject",
        backref="study_tasks",
    )

    chapter = relationship(
        "Chapter",
        backref="study_tasks",
    )


