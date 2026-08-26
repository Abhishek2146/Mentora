# 

"""
Revision models for Mentora
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    ForeignKey,
    Integer,
    Boolean,
    Date,
    JSON,
)
from sqlalchemy.orm import relationship, backref

from app.database.base import BaseModel


class RevisionSchedule(BaseModel):
    """
    Stores a user's revision schedule.
    """

    __tablename__ = "revision_schedules"

    # User who owns the revision schedule
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Optional syllabus association
    syllabus_id = Column(
        Integer,
        ForeignKey("syllabuses.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Schedule information
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

    # Status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_ai_generated = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Stores additional schedule configuration
    # Example:
    # {
    #     "daily_hours": 2,
    #     "preferred_time": "evening",
    #     "revision_frequency": "daily"
    # }
    schedule_data = Column(
        JSON,
        nullable=True,
    )

    # Relationships
    user = relationship(
        "User",
        backref=backref("revision_schedules", passive_deletes=True),
    )

    syllabus = relationship(
        "Syllabus",
        backref="revision_schedules",
    )

    revision_items = relationship(
        "RevisionItem",
        back_populates="schedule",
        cascade="all, delete-orphan",
    )


class RevisionItem(BaseModel):
    """
    Stores an individual revision task.
    """

    __tablename__ = "revision_items"

    schedule_id = Column(
        Integer,
        ForeignKey("revision_schedules.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Academic mapping
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

    # Revision information
    topic_name = Column(
        String(255),
        nullable=False,
    )

    scheduled_date = Column(
        Date,
        nullable=False,
    )

    revision_method = Column(
        String(50),
        default="review",
        nullable=False,
    )

    priority = Column(
        String(20),
        default="medium",
        nullable=False,
    )

    # Completion tracking
    completed = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    completion_percentage = Column(
        Integer,
        default=0,
        nullable=False,
    )

    # Optional notes
    notes = Column(
        Text,
        nullable=True,
    )

    # AI recommendation
    is_ai_recommended = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    recommendation = Column(
        Text,
        nullable=True,
    )

    # Relationships
    schedule = relationship(
        "RevisionSchedule",
        back_populates="revision_items",
    )

    subject = relationship(
        "Subject",
        backref="revision_items",
    )

    chapter = relationship(
        "Chapter",
        backref="revision_items",
    )