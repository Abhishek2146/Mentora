"""
Notification model
"""
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import BaseModel


class NotificationType(str, Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    REMINDER = "reminder"
    ACHIEVEMENT = "achievement"
    SYSTEM = "system"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(BaseModel):
    """Notification database model."""

    __tablename__ = "notifications"

    # User who receives the notification
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Notification type
    type = Column(
        String(20),
        default=NotificationType.INFO.value,
        nullable=False
    )

    # Notification priority
    priority = Column(
        String(10),
        default=NotificationPriority.NORMAL.value,
        nullable=False
    )

    # Notification title
    title = Column(
        String(255),
        nullable=False
    )

    # Notification message
    message = Column(
        Text,
        nullable=False
    )

    # Optional: related entity type (e.g., "quiz", "study_plan", "flashcard")
    related_entity_type = Column(
        String(50),
        nullable=True
    )

    # Optional: related entity ID
    related_entity_id = Column(
        Integer,
        nullable=True
    )

    # Whether the notification has been read
    is_read = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # Whether the notification has been archived
    is_archived = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # Read timestamp
    read_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationship to user
    user = relationship("User", back_populates="notifications")