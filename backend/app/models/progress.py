# 

"""
Progress and Weak Topic models
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship

from app.database.base import BaseModel


# ============================================================
# Progress Model
# ============================================================

class Progress(BaseModel):
    __tablename__ = "progress"

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

    syllabus_id = Column(
        Integer,
        ForeignKey("syllabuses.id"),
        nullable=True,
    )

    progress_type = Column(
        String(50),
        nullable=False,
    )

    value = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    target_value = Column(
        Float,
        default=100.0,
        nullable=False,
    )

    # "metadata" is reserved by SQLAlchemy.
    # Keep "metadata" as the database column name,
    # but use "progress_metadata" as the Python attribute.
    progress_metadata = Column(
        "metadata",
        JSON,
        nullable=True,
    )

    # --------------------------------------------------------
    # Relationships
    # --------------------------------------------------------

    user = relationship(
        "User",
        backref="progress",
    )

    subject = relationship(
        "Subject",
        backref="progress_entries",
    )

    chapter = relationship(
        "Chapter",
        backref="progress_entries",
    )

    syllabus = relationship(
        "Syllabus",
        backref="progress_entries",
    )


# ============================================================
# Weak Topic Model
# ============================================================

class WeakTopic(BaseModel):
    __tablename__ = "weak_topics"

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

    topic_name = Column(
        String(255),
        nullable=False,
    )

    accuracy = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    confidence_level = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    total_attempts = Column(
        Integer,
        default=0,
        nullable=False,
    )

    last_attempted = Column(
        Date,
        nullable=True,
    )

    recommended_action = Column(
        String(500),
        nullable=True,
    )

    # --------------------------------------------------------
    # Relationships
    # --------------------------------------------------------

    user = relationship(
        "User",
        backref="weak_topics",
    )

    syllabus = relationship(
        "Syllabus",
        backref="weak_topics",
    )

    subject = relationship(
        "Subject",
        backref="weak_topics",
    )

    chapter = relationship(
        "Chapter",
        backref="weak_topics",
    )

