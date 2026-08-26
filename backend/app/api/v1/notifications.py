"""
Notification API endpoints
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    NotificationOut,
    NotificationListResponse,
    NotificationStats,
    BulkNotificationAction,
    NotificationType,
    NotificationPriority
)
from app.services.notification_service import notification_service

router = APIRouter()


@router.post("", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new notification for the current user.

    (Typically used by system/services, not directly by users)
    """
    # Users can only create notifications for themselves unless admin
    if current_user.id != notification_data.user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create notifications for yourself"
        )

    notification = await notification_service.create_notification(db, notification_data)
    return notification


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    archived_only: bool = Query(False, description="Show only archived notifications"),
    notification_type: Optional[NotificationType] = Query(None, description="Filter by notification type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated notifications for the current user.
    """
    return await notification_service.get_user_notifications(
        db=db,
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        unread_only=unread_only,
        archived_only=archived_only,
        notification_type=notification_type
    )


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get notification statistics for the current user.
    """
    return await notification_service.get_notification_stats(db, current_user.id)


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the count of unread notifications for the current user.
    """
    stats = await notification_service.get_notification_stats(db, current_user.id)
    return {"unread_count": stats.unread}


@router.get("/{notification_id}", response_model=NotificationOut)
async def get_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific notification by ID.
    """
    notification = await notification_service.get_notification(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return notification


@router.patch("/{notification_id}", response_model=NotificationOut)
async def update_notification(
    notification_id: int,
    update_data: NotificationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a notification (mark as read/unread, archive/unarchive).
    """
    notification = await notification_service.get_notification(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    if update_data.is_read is not None:
        if update_data.is_read and not notification.is_read:
            notification = await notification_service.mark_as_read(db, notification_id, current_user.id)
        elif not update_data.is_read and notification.is_read:
            notification = await notification_service.mark_as_unread(db, notification_id, current_user.id)

    if update_data.is_archived is not None:
        if update_data.is_archived and not notification.is_archived:
            notification = await notification_service.archive_notification(db, notification_id, current_user.id)
        elif not update_data.is_archived and notification.is_archived:
            notification = await notification_service.unarchive_notification(db, notification_id, current_user.id)

    return notification


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a notification as read.
    """
    notification = await notification_service.mark_as_read(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return notification


@router.post("/{notification_id}/unread", response_model=NotificationOut)
async def mark_as_unread(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a notification as unread.
    """
    notification = await notification_service.mark_as_unread(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return notification


@router.post("/{notification_id}/archive", response_model=NotificationOut)
async def archive_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Archive a notification.
    """
    notification = await notification_service.archive_notification(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return notification


@router.post("/{notification_id}/unarchive", response_model=NotificationOut)
async def unarchive_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unarchive a notification.
    """
    notification = await notification_service.unarchive_notification(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return notification


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a notification.
    """
    deleted = await notification_service.delete_notification(db, notification_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )


@router.post("/bulk-action")
async def bulk_action(
    action_data: BulkNotificationAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform bulk action on multiple notifications.
    """
    result = await notification_service.bulk_action(db, current_user.id, action_data)
    return {
        "message": f"Bulk action '{action_data.action}' completed",
        "affected": result["affected"],
        "total": result["total"]
    }


@router.post("/mark-all-read")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark all unread notifications as read for the current user.
    """
    count = await notification_service.mark_all_as_read(db, current_user.id)
    return {"message": f"Marked {count} notifications as read", "count": count}