"""
Notification Service for managing user notifications.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType, NotificationPriority
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    NotificationOut,
    NotificationListResponse,
    NotificationStats,
    BulkNotificationAction
)


class NotificationService:
    """Service for managing notifications."""

    async def create_notification(
        self,
        db: AsyncSession,
        notification_data: NotificationCreate
    ) -> Notification:
        """
        Create a new notification.

        Args:
            db: Database session
            notification_data: Notification data

        Returns:
            Created notification
        """
        notification = Notification(
            user_id=notification_data.user_id,
            type=notification_data.type.value if hasattr(notification_data.type, 'value') else notification_data.type,
            priority=notification_data.priority.value if hasattr(notification_data.priority, 'value') else notification_data.priority,
            title=notification_data.title,
            message=notification_data.message,
            related_entity_type=notification_data.related_entity_type,
            related_entity_id=notification_data.related_entity_id,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    async def get_notification(
        self,
        db: AsyncSession,
        notification_id: int,
        user_id: int
    ) -> Optional[Notification]:
        """
        Get a notification by ID.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID (for ownership check)

        Returns:
            Notification if found and belongs to user
        """
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            )
        )
        return result.scalars().first()

    async def get_user_notifications(
        self,
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        per_page: int = 20,
        unread_only: bool = False,
        archived_only: bool = False,
        notification_type: Optional[NotificationType] = None
    ) -> NotificationListResponse:
        """
        Get paginated notifications for a user.

        Args:
            db: Database session
            user_id: User ID
            page: Page number (1-indexed)
            per_page: Items per page
            unread_only: Filter to unread notifications only
            archived_only: Filter to archived notifications only
            notification_type: Filter by notification type

        Returns:
            Paginated notification list with unread count
        """
        # Base query
        query = select(Notification).where(Notification.user_id == user_id)

        # Apply filters
        if unread_only:
            query = query.where(Notification.is_read == False)
        if archived_only:
            query = query.where(Notification.is_archived == True)
        else:
            query = query.where(Notification.is_archived == False)
        if notification_type:
            query = query.where(Notification.type == notification_type.value if hasattr(notification_type, 'value') else notification_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get unread count
        unread_query = select(func.count()).select_from(
            select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    Notification.is_archived == False
                )
            ).subquery()
        )
        unread_result = await db.execute(unread_query)
        unread_count = unread_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(desc(Notification.created_at))
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await db.execute(query)
        notifications = result.scalars().all()

        # Calculate total pages
        pages = (total + per_page - 1) // per_page

        return NotificationListResponse(
            items=[NotificationOut.model_validate(n) for n in notifications],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            unread_count=unread_count
        )

    async def mark_as_read(
        self,
        db: AsyncSession,
        notification_id: int,
        user_id: int
    ) -> Optional[Notification]:
        """
        Mark a notification as read.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID

        Returns:
            Updated notification if found
        """
        notification = await self.get_notification(db, notification_id, user_id)
        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            await db.commit()
            await db.refresh(notification)
        return notification

    async def mark_as_unread(
        self,
        db: AsyncSession,
        notification_id: int,
        user_id: int
    ) -> Optional[Notification]:
        """
        Mark a notification as unread.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID

        Returns:
            Updated notification if found
        """
        notification = await self.get_notification(db, notification_id, user_id)
        if notification and notification.is_read:
            notification.is_read = False
            notification.read_at = None
            await db.commit()
            await db.refresh(notification)
        return notification

    async def archive_notification(
        self,
        db: AsyncSession,
        notification_id: int,
        user_id: int
    ) -> Optional[Notification]:
        """
        Archive a notification.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID

        Returns:
            Updated notification if found
        """
        notification = await self.get_notification(db, notification_id, user_id)
        if notification and not notification.is_archived:
            notification.is_archived = True
            await db.commit()
            await db.refresh(notification)
        return notification

    async def unarchive_notification(
        self,
        db: AsyncSession,
        notification_id: int,
        user_id: int
    ) -> Optional[Notification]:
        """
        Unarchive a notification.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID

        Returns:
            Updated notification if found
        """
        notification = await self.get_notification(db, notification_id, user_id)
        if notification and notification.is_archived:
            notification.is_archived = False
            await db.commit()
            await db.refresh(notification)
        return notification

    async def delete_notification(
        self,
        db: AsyncSession,
        notification_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a notification.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        notification = await self.get_notification(db, notification_id, user_id)
        if notification:
            await db.delete(notification)
            await db.commit()
            return True
        return False

    async def bulk_action(
        self,
        db: AsyncSession,
        user_id: int,
        action_data: BulkNotificationAction
    ) -> Dict[str, int]:
        """
        Perform bulk action on notifications.

        Args:
            db: Database session
            user_id: User ID
            action_data: Bulk action data

        Returns:
            Dictionary with counts of affected notifications
        """
        notifications = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id.in_(action_data.notification_ids),
                    Notification.user_id == user_id
                )
            )
        )
        notifications = notifications.scalars().all()

        affected = 0
        for notification in notifications:
            if action_data.action == "read" and not notification.is_read:
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                affected += 1
            elif action_data.action == "unread" and notification.is_read:
                notification.is_read = False
                notification.read_at = None
                affected += 1
            elif action_data.action == "archive" and not notification.is_archived:
                notification.is_archived = True
                affected += 1
            elif action_data.action == "delete":
                await db.delete(notification)
                affected += 1

        await db.commit()
        return {"affected": affected, "total": len(action_data.notification_ids)}

    async def mark_all_as_read(
        self,
        db: AsyncSession,
        user_id: int
    ) -> int:
        """
        Mark all unread notifications as read for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    Notification.is_archived == False
                )
            )
        )
        notifications = result.scalars().all()

        count = 0
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            count += 1

        await db.commit()
        return count

    async def get_notification_stats(
        self,
        db: AsyncSession,
        user_id: int
    ) -> NotificationStats:
        """
        Get notification statistics for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Notification statistics
        """
        # Total notifications (non-archived)
        total_result = await db.execute(
            select(func.count()).select_from(
                select(Notification).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_archived == False
                    )
                ).subquery()
            )
        )
        total = total_result.scalar() or 0

        # Unread count
        unread_result = await db.execute(
            select(func.count()).select_from(
                select(Notification).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read == False,
                        Notification.is_archived == False
                    )
                ).subquery()
            )
        )
        unread = unread_result.scalar() or 0

        # Archived count
        archived_result = await db.execute(
            select(func.count()).select_from(
                select(Notification).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_archived == True
                    )
                ).subquery()
            )
        )
        archived = archived_result.scalar() or 0

        # By type
        type_result = await db.execute(
            select(Notification.type, func.count())
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_archived == False
                )
            )
            .group_by(Notification.type)
        )
        by_type = {row[0]: row[1] for row in type_result.all()}

        # By priority
        priority_result = await db.execute(
            select(Notification.priority, func.count())
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_archived == False
                )
            )
            .group_by(Notification.priority)
        )
        by_priority = {row[0]: row[1] for row in priority_result.all()}

        return NotificationStats(
            total=total,
            unread=unread,
            archived=archived,
            by_type=by_type,
            by_priority=by_priority
        )

    async def create_system_notification(
        self,
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None
    ) -> Notification:
        """
        Create a system notification for a user.

        Args:
            db: Database session
            user_id: User ID
            title: Notification title
            message: Notification message
            priority: Notification priority
            related_entity_type: Related entity type
            related_entity_id: Related entity ID

        Returns:
            Created notification
        """
        return await self.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                type=NotificationType.SYSTEM,
                priority=priority,
                title=title,
                message=message,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id
            )
        )

    async def create_achievement_notification(
        self,
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None
    ) -> Notification:
        """
        Create an achievement notification.

        Args:
            db: Database session
            user_id: User ID
            title: Notification title
            message: Notification message
            related_entity_type: Related entity type
            related_entity_id: Related entity ID

        Returns:
            Created notification
        """
        return await self.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                type=NotificationType.ACHIEVEMENT,
                priority=NotificationPriority.HIGH,
                title=title,
                message=message,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id
            )
        )

    async def create_reminder_notification(
        self,
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None
    ) -> Notification:
        """
        Create a reminder notification.

        Args:
            db: Database session
            user_id: User ID
            title: Notification title
            message: Notification message
            related_entity_type: Related entity type
            related_entity_id: Related entity ID

        Returns:
            Created notification
        """
        return await self.create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                type=NotificationType.REMINDER,
                priority=NotificationPriority.NORMAL,
                title=title,
                message=message,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id
            )
        )


notification_service = NotificationService()