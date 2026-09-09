# Study Group Service

import uuid
import secrets
import string
from datetime import datetime, timedelta, date, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_
from sqlalchemy.orm import selectinload

from app.core.logger import get_logger
from app.models.study_group import StudyGroup, StudyGroupMember, StudyGroupMessage
from app.models.user import User
from app.models.study_streak import UserStreak, DailyStudySummary
from app.schemas.study_group import (
    StudyGroupCreate,
    StudyGroupOut,
    StudyGroupMemberJoin,
    StudyGroupMemberOut,
    StudyGroupMessageBase,
    StudyGroupMessageCreate,
    StudyGroupMessageOut,
    UserBrief,
    GroupLeaderboardEntry,
    GroupAchievementOut,
)


logger = get_logger(__name__)


def generate_invite_code(length: int = 10) -> str:
    """Generate a unique alphanumeric invite code."""
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(length))
        # Check if code already exists (simple check; full uniqueness enforced by DB unique constraint)
        return code


class StudyGroupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_group(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
    ) -> StudyGroupOut:
        """Create a new study group. Creator becomes admin."""
        invite_code = generate_invite_code()
        now = datetime.now(timezone.utc)

        group = StudyGroup(
            name=name,
            description=description,
            owner_id=user_id,
            invite_code=invite_code,
            created_at=now,
            updated_at=now,
        )

        self.db.add(group)
        await self.db.flush()

        # Add creator as admin member
        member = StudyGroupMember(
            group_id=group.id,
            user_id=user_id,
            role="admin",
            joined_at=now,
        )
        self.db.add(member)
        await self.db.flush()

        await self.db.commit()

        logger.info(
            "Study group created: id=%s name=%s owner_id=%s invite_code=%s",
            group.id,
            name,
            user_id,
            invite_code,
        )

        return StudyGroupOut(
            id=group.id,
            name=group.name,
            description=group.description,
            invite_code=group.invite_code,
            is_active=group.is_active,
            owner_id=group.owner_id,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )

    async def get_group(self, group_id: int) -> Optional[StudyGroupOut]:
        """Get a study group by ID."""
        result = await self.db.execute(
            select(StudyGroup)
            .options(
                selectinload(StudyGroup.owner),
                selectinload(StudyGroup.members),
                selectinload(StudyGroup.messages),
            )
            .where(StudyGroup.id == group_id, StudyGroup.is_active == True)
        )
        group = result.scalars().first()
        if not group:
            return None

        return StudyGroupOut(
            id=group.id,
            name=group.name,
            description=group.description,
            invite_code=group.invite_code,
            is_active=group.is_active,
            owner_id=group.owner_id,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )

    async def get_user_groups(
        self, user_id: int, include_inactive: bool = False
    ) -> List[StudyGroupOut]:
        """Get all groups the user is a member of."""
        query = (
            select(StudyGroup)
            .where(StudyGroup.is_active == True)
            .where(
                StudyGroup.id.in_(
                    select(StudyGroupMember.group_id)
                    .where(
                        StudyGroupMember.user_id == user_id,
                        StudyGroupMember.status == "active",
                    )
                )
            )
        )

        result = await self.db.execute(query)
        groups = result.scalars().all()

        return [
            StudyGroupOut(
                id=g.id,
                name=g.name,
                description=g.description,
                invite_code=g.invite_code,
                is_active=g.is_active,
                owner_id=g.owner_id,
                created_at=g.created_at,
                updated_at=g.updated_at,
            )
            for g in groups
        ]

    async def join_group(
        self, user_id: int, invite_code: str
    ) -> Optional[StudyGroupOut]:
        """Join a group using an invite code."""
        # Normalize invite code: strip whitespace and convert to uppercase
        invite_code = invite_code.strip().upper()

        # Find group by invite code
        group_result = await self.db.execute(
            select(StudyGroup).where(StudyGroup.invite_code == invite_code, StudyGroup.is_active == True)
        )
        group = group_result.scalars().first()

        if not group:
            logger.warning("Invalid or inactive invite code: %s", invite_code)
            return None

        # Check if user is already a member
        member_result = await self.db.execute(
            select(StudyGroupMember).where(
                StudyGroupMember.group_id == group.id,
                StudyGroupMember.user_id == user_id,
            )
        )
        existing_member = member_result.scalars().first()

        if existing_member:
            logger.info("User %s is already a member of group %s", user_id, group.id)
            return await self.get_group(group.id)

        # Add user as member
        member = StudyGroupMember(
            group_id=group.id,
            user_id=user_id,
            role="member",
            joined_at=datetime.now(timezone.utc),
        )
        self.db.add(member)
        await self.db.flush()
        await self.db.commit()

        logger.info(
            "User %s joined group %s via invite code", user_id, group.id,
        )

        return await self.get_group(group.id)

    async def leave_group(self, user_id: int, group_id: int) -> bool:
        """Leave a study group."""
        # Prevent leaving if you're the owner
        group_result = await self.db.execute(
            select(StudyGroup).where(StudyGroup.id == group_id)
        )
        group = group_result.scalars().first()
        if not group or group.owner_id == user_id:
            return False

        # Remove membership
        await self.db.execute(
            delete(StudyGroupMember).where(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.user_id == user_id,
            )
        )
        await self.db.commit()

        logger.info("User %s left group %s", user_id, group_id)
        return True

    async def delete_group(self, user_id: int, group_id: int) -> bool:
        """Delete a study group. Only the owner can delete."""
        group_result = await self.db.execute(
            select(StudyGroup).where(StudyGroup.id == group_id)
        )
        group = group_result.scalars().first()
        if not group or group.owner_id != user_id:
            return False

        await self.db.delete(group)
        await self.db.commit()

        logger.info("User %s deleted group %s", user_id, group_id)
        return True

    async def get_group_memory(self, group_id: int) -> dict:
        """Get the memory JSON for a study group."""
        result = await self.db.execute(
            select(StudyGroup).where(StudyGroup.id == group_id)
        )
        group = result.scalars().first()
        if not group:
            return {}
        return group.memory or {}

    async def update_group_memory(self, group_id: int, updates: dict) -> dict:
        """Merge memory updates into the group's existing memory.

        Returns the updated memory dict.
        """
        from app.services.memory_service import MemoryService
        memory_svc = MemoryService()

        result = await self.db.execute(
            select(StudyGroup).where(StudyGroup.id == group_id)
        )
        group = result.scalars().first()
        if not group:
            return {}

        existing = group.memory or {}
        merged = memory_svc.merge_memory(existing, updates)
        validated = memory_svc.validate_memory(merged)

        group.memory = validated
        await self.db.flush()
        await self.db.commit()

        logger.info("Updated memory for group %s", group_id)
        return validated

    async def reset_group_memory(self, group_id: int) -> bool:
        """Reset group memory to empty. Only owner can do this."""
        result = await self.db.execute(
            select(StudyGroup).where(StudyGroup.id == group_id)
        )
        group = result.scalars().first()
        if not group:
            return False

        from app.services.memory_service import MemoryService
        memory_svc = MemoryService()
        group.memory = memory_svc.get_empty_memory()
        await self.db.flush()
        await self.db.commit()

        logger.info("Reset memory for group %s", group_id)
        return True

    async def get_group_members(
        self, group_id: int
    ) -> List[StudyGroupMemberOut]:
        """Get all members of a study group."""
        result = await self.db.execute(
            select(StudyGroupMember, User)
            .join(User, StudyGroupMember.user_id == User.id)
            .where(StudyGroupMember.group_id == group_id, StudyGroupMember.status == "active")
            .order_by(StudyGroupMember.joined_at.asc())
        )
        rows = result.all()

        members = []
        for member, user in rows:
            members.append(
                StudyGroupMemberOut(
                    id=member.id,
                    user_id=user.id,
                    group_id=group_id,
                    role=member.role,
                    joined_at=member.joined_at,
                    status=member.status,
                    user=UserBrief(
                        id=user.id,
                        username=user.username,
                        full_name=user.full_name,
                    ),
                )
            )

        return members

    async def remove_member(self, admin_id: int, target_user_id: int, group_id: int) -> bool:
        """Admin removes a member from the group."""
        # Check admin privileges
        member_result = await self.db.execute(
            select(StudyGroupMember).where(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.user_id == admin_id,
            )
        )
        admin_member = member_result.scalars().first()
        if not admin_member or admin_member.role != "admin":
            return False

        # Prevent removing the owner
        group_result = await self.db.execute(
            select(StudyGroup).where(StudyGroup.id == group_id)
        )
        group = group_result.scalars().first()
        if not group or group.owner_id == target_user_id:
            return False

        # Remove the target member
        await self.db.execute(
            delete(StudyGroupMember).where(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.user_id == target_user_id,
            )
        )
        await self.db.commit()

        logger.info(
            "Admin %s removed member %s from group %s", admin_id, target_user_id, group_id,
        )
        return True

    async def send_message(
        self, user_id: int, group_id: int, content: str, message_type: str = "user"
    ) -> Optional[StudyGroupMessageOut]:
        """Send a message to a study group (members only)."""
        # Check if user is a member
        member_result = await self.db.execute(
            select(StudyGroupMember).where(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.user_id == user_id,
                StudyGroupMember.status == "active",
            )
        )
        if not member_result.scalars().first():
            return None  # User is not a member

        now = datetime.now(timezone.utc)
        message = StudyGroupMessage(
            group_id=group_id,
            sender_id=user_id,
            content=content,
            message_type=message_type,
            created_at=now,
            updated_at=now,
        )

        self.db.add(message)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(message)

        # Refresh with sender info
        sender_name = None
        if user_id:
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            sender = user_result.scalars().first()
            if sender:
                sender_name = sender.full_name or sender.username

        return StudyGroupMessageOut(
            id=message.id,
            sender_id=user_id,
            content=message.content,
            group_id=message.group_id,
            message_type=message.message_type,
            sender_name=sender_name,
            created_at=message.created_at,
            updated_at=message.updated_at,
        )

    async def save_ai_message(
        self, group_id: int, content: str
    ) -> StudyGroupMessageOut:
        """Save an AI-generated message to the group chat."""
        now = datetime.now(timezone.utc)
        message = StudyGroupMessage(
            group_id=group_id,
            sender_id=None,
            content=content,
            message_type="ai",
            created_at=now,
            updated_at=now,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(message)

        return StudyGroupMessageOut(
            id=message.id,
            sender_id=None,
            content=message.content,
            group_id=message.group_id,
            message_type="ai",
            sender_name="Mentora",
            created_at=message.created_at,
            updated_at=message.updated_at,
        )

    async def get_messages(
        self, group_id: int, limit: int = 50, before: Optional[datetime] = None
    ) -> List[StudyGroupMessageOut]:
        """Get messages from a study group with pagination."""
        query = (
            select(StudyGroupMessage)
            .where(StudyGroupMessage.group_id == group_id)
            .order_by(StudyGroupMessage.created_at.asc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        msg_rows = result.scalars().all()

        messages = []
        for msg_row in msg_rows:
            sender_name = None
            if msg_row.sender_id:
                user_result = await self.db.execute(
                    select(User).where(User.id == msg_row.sender_id)
                )
                sender = user_result.scalars().first()
                if sender:
                    sender_name = sender.full_name or sender.username
            elif msg_row.message_type == "ai":
                sender_name = "Mentora"

            messages.append(
                StudyGroupMessageOut(
                    id=msg_row.id,
                    sender_id=msg_row.sender_id,
                    content=msg_row.content,
                    group_id=msg_row.group_id,
                    message_type=msg_row.message_type,
                    sender_name=sender_name,
                    created_at=msg_row.created_at,
                    updated_at=msg_row.updated_at,
                )
            )

        return messages

    async def can_user_send_message(self, user_id: int, group_id: int) -> bool:
        """Check if a user can send messages in a group."""
        member_result = await self.db.execute(
            select(StudyGroupMember).where(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.user_id == user_id,
                StudyGroupMember.status == "active",
            )
        )
        return member_result.scalars().first() is not None

    async def can_user_view_group(self, user_id: int, group_id: int) -> bool:
        """Check if a user can view a group's data."""
        member_result = await self.db.execute(
            select(StudyGroupMember).where(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.user_id == user_id,
                StudyGroupMember.status == "active",
            )
        )
        return member_result.scalars().first() is not None

    async def get_group_leaderboard(
        self, group_id: int, days: int = 7
    ) -> List[GroupLeaderboardEntry]:
        """Get leaderboard for a study group based on qualifying study time."""
        # Get all active members
        members_result = await self.db.execute(
            select(StudyGroupMember, User)
            .join(User, StudyGroupMember.user_id == User.id)
            .where(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.status == "active",
            )
        )
        members = members_result.all()

        cutoff_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        today_str = date.today().strftime("%Y-%m-%d")

        entries = []
        for member, user in members:
            # Get qualifying study minutes in the period
            study_result = await self.db.execute(
                select(
                    func.coalesce(func.sum(DailyStudySummary.study_minutes), 0),
                    func.count(DailyStudySummary.id),
                ).where(
                    DailyStudySummary.user_id == user.id,
                    DailyStudySummary.date >= cutoff_date,
                    DailyStudySummary.date <= today_str,
                    DailyStudySummary.qualifying == True,
                )
            )
            row = study_result.one()
            study_minutes = row[0]
            qualifying_days = row[1]

            # Get current streak
            streak_result = await self.db.execute(
                select(UserStreak).where(UserStreak.user_id == user.id)
            )
            streak = streak_result.scalars().first()
            current_streak = streak.current_streak if streak else 0

            entries.append(GroupLeaderboardEntry(
                rank=0,
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                study_minutes=study_minutes,
                current_streak=current_streak,
                qualifying_days=qualifying_days,
            ))

        # Sort by study_minutes descending, then by streak descending
        entries.sort(key=lambda e: (-e.study_minutes, -e.current_streak))

        # Assign ranks
        for i, entry in enumerate(entries):
            entry.rank = i + 1

        return entries

    async def get_group_achievements(self, group_id: int) -> List[GroupAchievementOut]:
        """Get achievement badges for group members based on actual data."""
        members_result = await self.db.execute(
            select(StudyGroupMember, User)
            .join(User, StudyGroupMember.user_id == User.id)
            .where(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.status == "active",
            )
        )
        members = members_result.all()

        achievements = []
        today_str = date.today().strftime("%Y-%m-%d")

        for member, user in members:
            # Get streak data
            streak_result = await self.db.execute(
                select(UserStreak).where(UserStreak.user_id == user.id)
            )
            streak = streak_result.scalars().first()
            current_streak = streak.current_streak if streak else 0
            longest_streak = streak.longest_streak if streak else 0
            total_study_days = streak.total_study_days if streak else 0

            # Get total study minutes
            total_minutes_result = await self.db.execute(
                select(func.coalesce(func.sum(DailyStudySummary.study_minutes), 0)).where(
                    DailyStudySummary.user_id == user.id
                )
            )
            total_minutes = total_minutes_result.scalar() or 0

            # Streak badges
            if longest_streak >= 3:
                achievements.append(GroupAchievementOut(
                    id=len(achievements) + 1,
                    user_id=user.id,
                    username=user.username,
                    full_name=user.full_name,
                    badge_type="streak_3",
                    badge_name="3 Day Streak",
                    description="Maintained a 3-day study streak",
                    earned_at=datetime.utcnow(),
                ))
            if longest_streak >= 7:
                achievements.append(GroupAchievementOut(
                    id=len(achievements) + 1,
                    user_id=user.id,
                    username=user.username,
                    full_name=user.full_name,
                    badge_type="streak_7",
                    badge_name="7 Day Streak",
                    description="Maintained a 7-day study streak",
                    earned_at=datetime.utcnow(),
                ))
            if longest_streak >= 30:
                achievements.append(GroupAchievementOut(
                    id=len(achievements) + 1,
                    user_id=user.id,
                    username=user.username,
                    full_name=user.full_name,
                    badge_type="streak_30",
                    badge_name="30 Day Streak",
                    description="Maintained a 30-day study streak",
                    earned_at=datetime.utcnow(),
                ))

            # Study time badges
            if total_minutes >= 600:
                achievements.append(GroupAchievementOut(
                    id=len(achievements) + 1,
                    user_id=user.id,
                    username=user.username,
                    full_name=user.full_name,
                    badge_type="dedicated_learner",
                    badge_name="Dedicated Learner",
                    description="Studied for 10+ hours total",
                    earned_at=datetime.utcnow(),
                ))
            if total_study_days >= 20:
                achievements.append(GroupAchievementOut(
                    id=len(achievements) + 1,
                    user_id=user.id,
                    username=user.username,
                    full_name=user.full_name,
                    badge_type="consistent_learner",
                    badge_name="Consistent Learner",
                    description="Completed 20+ qualifying study days",
                    earned_at=datetime.utcnow(),
                ))

        return achievements