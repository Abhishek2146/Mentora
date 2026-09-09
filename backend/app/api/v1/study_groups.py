# Study Group API Endpoints

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.user import User
from app.models.study_group import StudyGroup
from app.schemas.study_group import (
    StudyGroupCreate,
    StudyGroupOut,
    StudyGroupMemberJoin,
    StudyGroupMemberOut,
    StudyGroupMessageCreate,
    StudyGroupMessageOut,
    GroupLeaderboardEntry,
    GroupAchievementOut,
    GroupMemoryOut,
)
from app.services.study_group_service import StudyGroupService
from app.services.tutor_service import TutorService
from app.services.memory_service import MemoryService
from app.core.logger import get_logger

router = APIRouter()
tutor_service = TutorService()
memory_service = MemoryService()
logger = get_logger(__name__)


def get_study_group_service(db: AsyncSession = Depends(get_db)) -> StudyGroupService:
    return StudyGroupService(db)


@router.post("/", response_model=StudyGroupOut, status_code=status.HTTP_201_CREATED)
async def create_study_group(
    group_data: StudyGroupCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new study group. Creator becomes admin."""
    service = get_study_group_service(db)
    return await service.create_group(user_id=user_id, name=group_data.name, description=group_data.description)


@router.get("/", response_model=List[StudyGroupOut])
async def list_user_groups(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    include_inactive: bool = False,
):
    """Get all groups the user is a member of."""
    service = get_study_group_service(db)
    return await service.get_user_groups(user_id=user_id, include_inactive=include_inactive)


@router.get("/{group_id}", response_model=StudyGroupOut)
async def get_study_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get a study group by ID."""
    service = get_study_group_service(db)
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study group not found",
        )
    # Check if user is a member
    if not await service.can_user_view_group(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )
    return group


@router.post("/join", response_model=StudyGroupOut)
async def join_study_group(
    join_data: StudyGroupMemberJoin,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Join a study group using an invite code."""
    service = get_study_group_service(db)
    group = await service.join_group(user_id=user_id, invite_code=join_data.invite_code)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inactive invite code, or you are already a member",
        )
    return group


@router.post("/{group_id}/leave")
async def leave_study_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Leave a study group."""
    service = get_study_group_service(db)
    removed = await service.leave_group(user_id=user_id, group_id=group_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot leave group: you are the owner or group not found",
        )
    return {"detail": "Left study group successfully"}


@router.delete("/{group_id}")
async def delete_study_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a study group. Only the owner can delete."""
    service = get_study_group_service(db)
    deleted = await service.delete_group(user_id=user_id, group_id=group_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group owner can delete the group",
        )
    return {"detail": "Group deleted successfully"}


@router.get("/{group_id}/members", response_model=List[StudyGroupMemberOut])
async def get_group_members(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get all members of a study group."""
    service = get_study_group_service(db)
    # Check if user is a member
    if not await service.can_user_view_group(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )
    members = await service.get_group_members(group_id=group_id)
    return members


@router.delete("/{group_id}/members/{user_id}")
async def remove_group_member(
    group_id: int,
    user_id: int,
    admin_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Admin removes a member from the group."""
    service = get_study_group_service(db)
    removed = await service.remove_member(
        admin_id=admin_id, target_user_id=user_id, group_id=group_id,
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required or cannot remove owner",
        )
    return {"detail": "Member removed successfully"}


@router.post("/{group_id}/messages", response_model=StudyGroupMessageOut)
async def send_group_message(
    group_id: int,
    message_data: StudyGroupMessageCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Send a message to a study group. Handles /mentora commands."""
    service = StudyGroupService(db)
    # Check if group exists and user is a member
    group_result = await db.execute(
        select(StudyGroup).where(StudyGroup.id == group_id, StudyGroup.is_active == True)
    )
    group = group_result.scalars().first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study group not found",
        )

    if not await service.can_user_send_message(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a group member to send messages",
        )

    content = message_data.content.strip()

    # Handle /mentora command
    if content.lower().startswith("/mentora"):
        prompt = content[len("/mentora"):].strip()
        if not prompt:
            # Save user's empty command as a message first
            user_msg = await service.send_message(
                user_id=user_id, group_id=group_id, content=content, message_type="user"
            )
            # Then save AI hint
            await service.save_ai_message(
                group_id=group_id,
                content="Please provide a question after /mentora. For example: /mentora explain RAG",
            )
            return user_msg

        # Get recent group messages for context (last 10)
        recent_msgs = await service.get_messages(group_id=group_id, limit=10)
        context_parts = []
        for m in recent_msgs:
            if m.message_type == "ai":
                context_parts.append(f"Mentora: {m.content[:200]}")
            elif m.sender_name:
                context_parts.append(f"{m.sender_name}: {m.content[:200]}")
        context_str = "\n".join(context_parts[-5:]) if context_parts else ""

        # Get group memory for context
        group_memory = await service.get_group_memory(group_id)
        memory_str = memory_service.format_memory_for_prompt(group_memory)

        # Build a contextual prompt for group chat with memory
        group_prompt = prompt
        parts = []
        if context_str:
            parts.append(f"RECENT GROUP CONVERSATION:\n{context_str}")
        if memory_str and memory_str != "No group memory available yet.":
            parts.append(f"GROUP LEARNING CONTEXT:\n{memory_str}")
        parts.append(f"CURRENT REQUEST:\n{prompt}")
        group_prompt = "\n\n".join(parts)

        try:
            ai_result = await tutor_service.process_message(
                user_id=user_id,
                message=group_prompt,
                db=db,
            )
            ai_response = ai_result.get("response", "Sorry, I couldn't process that request right now.")
        except Exception as e:
            logger.error("Mentora AI error in group %s: %s", group_id, str(e))
            ai_response = "Sorry, I couldn't process that request right now. Please try again later."

        # Save user's command as a message first
        user_msg = await service.send_message(
            user_id=user_id, group_id=group_id, content=content, message_type="user"
        )

        # Then save AI response
        ai_msg = await service.save_ai_message(group_id=group_id, content=ai_response)

        # Extract and update group memory (non-blocking, best-effort)
        try:
            conversation = "\n".join(context_parts[-5:]) if context_str else ""
            updates = await memory_service.extract_memory(
                current_memory=group_memory,
                conversation=conversation,
                question=prompt,
                response=ai_response,
            )
            if updates:
                await service.update_group_memory(group_id, updates)
        except Exception as e:
            logger.warning("Memory extraction failed for group %s: %s", group_id, str(e))

        # Return the AI message (frontend will refetch messages to see both)
        return ai_msg

    # Normal message
    return await service.send_message(
        user_id=user_id, group_id=group_id, content=content, message_type="user"
    )


@router.get("/{group_id}/memory", response_model=GroupMemoryOut)
async def get_group_memory(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get the learning memory for a study group. Members only."""
    service = StudyGroupService(db)
    if not await service.can_user_view_group(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a group member to view group memory",
        )
    memory = await service.get_group_memory(group_id)
    return GroupMemoryOut(group_id=group_id, memory=memory)


@router.delete("/{group_id}/memory")
async def reset_group_memory(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Reset group memory to empty. Only the group owner can do this."""
    service = StudyGroupService(db)
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study group not found",
        )
    if group.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group owner can reset memory",
        )
    await service.reset_group_memory(group_id)
    return {"detail": "Group memory reset successfully"}


@router.get("/{group_id}/leaderboard", response_model=List[GroupLeaderboardEntry])
async def get_group_leaderboard(
    group_id: int,
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get leaderboard for a study group."""
    service = StudyGroupService(db)
    if not await service.can_user_view_group(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a group member to view the leaderboard",
        )
    return await service.get_group_leaderboard(group_id=group_id, days=days)


@router.get("/{group_id}/achievements", response_model=List[GroupAchievementOut])
async def get_group_achievements(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get achievement badges for group members."""
    service = StudyGroupService(db)
    if not await service.can_user_view_group(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a group member to view achievements",
        )
    return await service.get_group_achievements(group_id=group_id)


@router.get("/{group_id}/messages", response_model=List[StudyGroupMessageOut])
async def get_group_messages(
    group_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get messages from a study group."""
    service = get_study_group_service(db)
    # Check if user is a member
    if not await service.can_user_view_group(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a group member to view messages",
        )

    messages = await service.get_messages(group_id=group_id, limit=limit)
    return messages