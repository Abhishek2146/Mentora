"""
Notification schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.notification import NotificationType, NotificationPriority


class NotificationBase(BaseModel):
    """Base notification schema."""
    type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None


class NotificationCreate(NotificationBase):
    """Schema for creating a notification."""
    user_id: int


class NotificationUpdate(BaseModel):
    """Schema for updating a notification."""
    is_read: Optional[bool] = None
    is_archived: Optional[bool] = None


class NotificationOut(NotificationBase):
    """Schema for notification output."""
    id: int
    user_id: int
    is_read: bool
    is_archived: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Response for paginated notification list."""
    items: List[NotificationOut]
    total: int
    page: int
    per_page: int
    pages: int
    unread_count: int


class BulkNotificationAction(BaseModel):
    """Schema for bulk notification actions."""
    notification_ids: List[int] = Field(..., min_length=1)
    action: str = Field(..., pattern="^(read|unread|archive|delete)$")


class NotificationStats(BaseModel):
    """Notification statistics."""
    total: int
    unread: int
    archived: int
    by_type: dict
    by_priority: dict