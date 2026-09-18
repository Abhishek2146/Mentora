# Study Group API Endpoints

import os
import socket
import secrets
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_user_id
from app.core.config import settings
from app.database.database import get_db
from app.models.user import User
from app.models.study_group import (
    StudyGroup,
    StudyGroupMember,
    StudyGroupMessage,
    StudyGroupInvitation,
    generate_invite_token,
)
from app.schemas.study_group import (
    StudyGroupCreate,
    StudyGroupOut,
    StudyGroupMemberJoin,
    StudyGroupMemberOut,
    StudyGroupMessageCreate,
    StudyGroupMessageOut,
    StudyGroupMessageEdit,
    StudyGroupMessageForward,
    GroupLeaderboardEntry,
    GroupAchievementOut,
    GroupMemoryOut,
    InvitationByUsername,
    InvitationByEmail,
    StudyGroupInvitationOut,
    InviteLinkOut,
)
from app.services.study_group_service import StudyGroupService
from app.services.tutor_service import TutorService
from app.services.memory_service import MemoryService
from app.services.email_service import email_service
from app.core.logger import get_logger

router = APIRouter()
tutor_service = TutorService()
memory_service = MemoryService()
logger = get_logger(__name__)

FRONTEND_DEFAULT_PORT = 5173


def _get_lan_ip() -> str:
    """Return the machine's primary outbound IP (LAN) for building shareable links."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)
        sock.connect(("8.8.8.8", 80))  # no packets sent, just route selection
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "localhost"


def _resolve_frontend_base(request: Request) -> str:
    """Resolve a frontend base URL that other machines on the network can reach.

    Priority:
      1. Explicit settings.FRONTEND_URL (domain / LAN IP / tunnel URL).
      2. The request's Origin header (the exact URL the browser is using).
      3. The request's Host header (when accessed via IP/hostname, not localhost).
      4. The machine's LAN IP + default frontend dev port.
    """
    configured = (settings.FRONTEND_URL or "").strip().rstrip("/")
    if configured and configured != "http://localhost:5173":
        return configured

    origin = (request.headers.get("origin") or "").strip().rstrip("/")
    if origin and "localhost" not in origin and "127.0.0.1" not in origin:
        return origin

    host = (request.headers.get("host") or "").strip()
    if host and "localhost" not in host and "127.0.0.1" not in host:
        return f"{request.url.scheme}://{host}".rstrip("/")

    port = os.getenv("FRONTEND_PORT", str(FRONTEND_DEFAULT_PORT))
    return f"http://{_get_lan_ip()}:{port}"


def get_study_group_service(db: AsyncSession = Depends(get_db)) -> StudyGroupService:
    return StudyGroupService(db)


# ============================================================
# Group CRUD (existing endpoints - preserved)
# ============================================================


@router.post("/", response_model=StudyGroupOut, status_code=status.HTTP_201_CREATED)
async def create_study_group(
    group_data: StudyGroupCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new study group. Creator becomes admin."""
    service = get_study_group_service(db)
    group = await service.create_group(
        user_id=user_id, name=group_data.name, description=group_data.description
    )
    # Generate invite token for the new group
    group_result = await db.execute(
        select(StudyGroup).where(StudyGroup.id == group.id)
    )
    db_group = group_result.scalars().first()
    if db_group and not db_group.invite_token:
        db_group.invite_token = generate_invite_token()
        await db.commit()
        await db.refresh(db_group)
        group.invite_token = db_group.invite_token
    return group


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
    if not await service.can_user_view_group(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )
    return group


# ============================================================
# Join Group (kept for backward compatibility)
# ============================================================


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
    # Ensure invite token exists
    group_result = await db.execute(
        select(StudyGroup).where(StudyGroup.id == group.id)
    )
    db_group = group_result.scalars().first()
    if db_group and not db_group.invite_token:
        db_group.invite_token = generate_invite_token()
        await db.commit()
    return group


# ============================================================
# Join by Invitation Link (new)
# ============================================================


@router.get("/join/{token}", response_model=StudyGroupOut)
async def join_by_invite_token(
    token: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Join a study group using a secure invitation link token."""
    # Find group by invite token
    result = await db.execute(
        select(StudyGroup).where(
            StudyGroup.invite_token == token,
            StudyGroup.is_active == True,
        )
    )
    group = result.scalars().first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation link",
        )

    service = get_study_group_service(db)

    # Check if already a member
    if await service.can_user_view_group(user_id, group.id):
        return await service.get_group(group.id)

    # Add as member
    member = StudyGroupMember(
        group_id=group.id,
        user_id=user_id,
        role="member",
        joined_at=datetime.now(timezone.utc),
    )
    db.add(member)
    await db.commit()

    logger.info("User %s joined group %s via invite link", user_id, group.id)
    return await service.get_group(group.id)


# ============================================================
# Leave / Delete (existing - preserved)
# ============================================================


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


# ============================================================
# Members (existing - preserved)
# ============================================================


@router.get("/{group_id}/members", response_model=List[StudyGroupMemberOut])
async def get_group_members(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get all members of a study group."""
    service = get_study_group_service(db)
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


# ============================================================
# Messages (existing + improved pagination)
# ============================================================


@router.post("/{group_id}/messages", response_model=StudyGroupMessageOut)
async def send_group_message(
    group_id: int,
    message_data: StudyGroupMessageCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Send a message to a study group. Handles /mentora commands via REST API."""
    service = StudyGroupService(db)
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
            user_msg = await service.send_message(
                user_id=user_id, group_id=group_id, content=content, message_type="user"
            )
            await service.save_ai_message(
                group_id=group_id,
                content="Please provide a question after /mentora. For example: /mentora explain RAG",
            )
            return user_msg

        recent_msgs = await service.get_messages(group_id=group_id, limit=10)
        context_parts = []
        for m in recent_msgs:
            if m.message_type == "ai":
                context_parts.append(f"Mentora: {m.content[:200]}")
            elif m.sender_name:
                context_parts.append(f"{m.sender_name}: {m.content[:200]}")
        context_str = "\n".join(context_parts[-5:]) if context_parts else ""

        group_memory = await service.get_group_memory(group_id)
        memory_str = memory_service.format_memory_for_prompt(group_memory)

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

        user_msg = await service.send_message(
            user_id=user_id, group_id=group_id, content=content, message_type="user"
        )
        ai_msg = await service.save_ai_message(group_id=group_id, content=ai_response)

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

        return ai_msg

    # Normal message
    return await service.send_message(
        user_id=user_id, group_id=group_id, content=content, message_type="user"
    )


@router.get("/{group_id}/messages", response_model=List[StudyGroupMessageOut])
async def get_group_messages(
    group_id: int,
    limit: int = Query(50, ge=1, le=200),
    before: Optional[int] = Query(None, description="Message ID cursor for pagination"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get messages from a study group with cursor-based pagination.

    Use `before=<message_id>` to fetch older messages.
    The response returns the latest `limit` messages if no cursor is provided.
    """
    service = get_study_group_service(db)
    if not await service.can_user_view_group(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a group member to view messages",
        )

    messages = await service.get_messages(group_id=group_id, limit=limit, before=before)
    return messages


@router.patch("/{group_id}/messages/{message_id}", response_model=StudyGroupMessageOut)
async def edit_group_message(
    group_id: int,
    message_id: int,
    data: StudyGroupMessageEdit,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Edit a message. Only the sender can edit their own messages."""
    service = get_study_group_service(db)
    if not await service.can_user_send_message(user_id, group_id):
        raise HTTPException(status_code=403, detail="You must be a group member")

    result = await service.edit_message(
        user_id=user_id, group_id=group_id, message_id=message_id, new_content=data.content.strip()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Message not found or cannot be edited")
    return result


@router.delete("/{group_id}/messages/{message_id}", response_model=StudyGroupMessageOut)
async def delete_group_message(
    group_id: int,
    message_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Soft-delete a message. Any active group member can remove any message."""
    service = get_study_group_service(db)
    if not await service.can_user_send_message(user_id, group_id):
        raise HTTPException(status_code=403, detail="You must be a group member")

    result = await service.delete_message(user_id=user_id, group_id=group_id, message_id=message_id)
    if not result:
        raise HTTPException(status_code=404, detail="Message not found or cannot be deleted")
    return result


@router.post("/{group_id}/messages/{message_id}/forward", response_model=List[StudyGroupMessageOut])
async def forward_group_message(
    group_id: int,
    message_id: int,
    data: StudyGroupMessageForward,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Forward a message to one or more groups."""
    service = get_study_group_service(db)
    if not await service.can_user_send_message(user_id, group_id):
        raise HTTPException(status_code=403, detail="You must be a group member")

    results = await service.forward_message(
        user_id=user_id,
        source_group_id=group_id,
        message_id=message_id,
        target_group_ids=data.target_group_ids,
    )
    if not results:
        raise HTTPException(status_code=404, detail="Message not found or no valid target groups")
    return results


# ============================================================
# Invitations (new system)
# ============================================================


@router.post("/{group_id}/invitations/by-username", response_model=StudyGroupInvitationOut)
async def invite_by_username(
    group_id: int,
    data: InvitationByUsername,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Invite a user to the group by username. Admin/Owner only."""
    service = get_study_group_service(db)

    # Check group exists
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Study group not found")

    # Check caller is admin
    admin_check = await db.execute(
        select(StudyGroupMember).where(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == user_id,
            StudyGroupMember.status == "active",
        )
    )
    admin_member = admin_check.scalars().first()
    if not admin_member or admin_member.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Find target user by username
    target_result = await db.execute(
        select(User).where(User.username == data.username, User.is_active == True)
    )
    target_user = target_result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check not already a member
    if await service.can_user_view_group(target_user.id, group_id):
        raise HTTPException(status_code=400, detail="User is already a member")

    # Check for existing pending invitation
    existing = await db.execute(
        select(StudyGroupInvitation).where(
            StudyGroupInvitation.group_id == group_id,
            StudyGroupInvitation.invited_user_id == target_user.id,
            StudyGroupInvitation.status == "pending",
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Invitation already pending")

    # Create invitation
    invitation = StudyGroupInvitation(
        group_id=group_id,
        invited_user_id=target_user.id,
        invited_by=user_id,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    # Create notification for invited user
    from app.models.notification import Notification
    inviter_result = await db.execute(select(User).where(User.id == user_id))
    inviter = inviter_result.scalars().first()
    inviter_name = inviter.full_name or inviter.username if inviter else "Someone"

    notification = Notification(
        user_id=target_user.id,
        type="info",
        priority="normal",
        title="Study Group Invitation",
        message=f'{inviter_name} invited you to join "{group.name}"',
        related_entity_type="study_group_invitation",
        related_entity_id=invitation.id,
    )
    db.add(notification)
    await db.commit()

    return StudyGroupInvitationOut(
        id=invitation.id,
        group_id=invitation.group_id,
        group_name=group.name,
        invited_user_id=invitation.invited_user_id,
        invited_by=invitation.invited_by,
        inviter_name=inviter_name,
        status=invitation.status,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
    )


@router.post("/{group_id}/invitations/by-email", response_model=StudyGroupInvitationOut)
async def invite_by_email(
    group_id: int,
    data: InvitationByEmail,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Invite a user to the group by email. Admin/Owner only. Emails an invite link."""
    service = get_study_group_service(db)

    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Study group not found")

    admin_check = await db.execute(
        select(StudyGroupMember).where(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == user_id,
            StudyGroupMember.status == "active",
        )
    )
    admin_member = admin_check.scalars().first()
    if not admin_member or admin_member.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Find user by email
    target_result = await db.execute(
        select(User).where(User.email == data.email, User.is_active == True)
    )
    target_user = target_result.scalars().first()

    # Check not already a member
    if target_user and await service.can_user_view_group(target_user.id, group_id):
        raise HTTPException(status_code=400, detail="User is already a member")

    # Check for existing pending invitation
    if target_user:
        existing = await db.execute(
            select(StudyGroupInvitation).where(
                StudyGroupInvitation.group_id == group_id,
                StudyGroupInvitation.invited_user_id == target_user.id,
                StudyGroupInvitation.status == "pending",
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Invitation already pending")

    # Create invitation
    invitation = StudyGroupInvitation(
        group_id=group_id,
        invited_user_id=target_user.id if target_user else None,
        invited_email=data.email,
        invited_by=user_id,
        token=secrets.token_urlsafe(32),
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    # Create notification if user exists
    if target_user:
        from app.models.notification import Notification
        inviter_result = await db.execute(select(User).where(User.id == user_id))
        inviter = inviter_result.scalars().first()
        inviter_name = inviter.full_name or inviter.username if inviter else "Someone"

        notification = Notification(
            user_id=target_user.id,
            type="info",
            priority="normal",
            title="Study Group Invitation",
            message=f'{inviter_name} invited you to join "{group.name}"',
            related_entity_type="study_group_invitation",
            related_entity_id=invitation.id,
        )
        db.add(notification)
        await db.commit()

    # Send the invitation email with a direct join link
    inviter_result = await db.execute(select(User).where(User.id == user_id))
    inviter = inviter_result.scalars().first()
    inviter_name = inviter.full_name or inviter.username if inviter else "Someone"

    frontend_base = _resolve_frontend_base(request)
    group_token = group.invite_token
    if not group_token:
        group_token = generate_invite_token()
        db_group = await db.execute(select(StudyGroup).where(StudyGroup.id == group_id))
        db_group_obj = db_group.scalars().first()
        db_group_obj.invite_token = group_token
        await db.commit()
    join_link = f"{frontend_base}/study-groups/join/{group_token}"

    email_sent = await email_service.send_group_invitation_email(
        to_email=data.email,
        group_name=group.name,
        inviter_name=inviter_name,
        join_link=join_link,
        frontend_url=frontend_base,
    )
    if not email_sent:
        logger.warning(
            "Invitation email not sent (check SMTP config). DEV JOIN LINK for %s: %s",
            data.email,
            join_link,
        )

    return StudyGroupInvitationOut(
        id=invitation.id,
        group_id=invitation.group_id,
        group_name=group.name,
        invited_user_id=invitation.invited_user_id,
        invited_email=invitation.invited_email,
        invited_by=invitation.invited_by,
        status=invitation.status,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
    )


@router.get("/invitations", response_model=List[StudyGroupInvitationOut])
async def list_my_invitations(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List invitations sent to or by the current user."""
    query = select(StudyGroupInvitation).where(
        (StudyGroupInvitation.invited_user_id == user_id)
        | (StudyGroupInvitation.invited_by == user_id)
    )
    if status_filter:
        query = query.where(StudyGroupInvitation.status == status_filter)
    query = query.order_by(StudyGroupInvitation.created_at.desc()).limit(50)

    result = await db.execute(query)
    invitations = result.scalars().all()

    out = []
    for inv in invitations:
        # Fetch group name
        group_result = await db.execute(select(StudyGroup).where(StudyGroup.id == inv.group_id))
        grp = group_result.scalars().first()
        # Fetch inviter name
        inviter_result = await db.execute(select(User).where(User.id == inv.invited_by))
        inviter = inviter_result.scalars().first()
        inviter_name = inviter.full_name or inviter.username if inviter else None

        out.append(StudyGroupInvitationOut(
            id=inv.id,
            group_id=inv.group_id,
            group_name=grp.name if grp else None,
            invited_user_id=inv.invited_user_id,
            invited_email=inv.invited_email,
            invited_by=inv.invited_by,
            inviter_name=inviter_name,
            status=inv.status,
            token=inv.token,
            created_at=inv.created_at,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at,
        ))
    return out


@router.post("/invitations/{invitation_id}/accept", response_model=StudyGroupOut)
async def accept_invitation(
    invitation_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Accept a pending study group invitation."""
    result = await db.execute(
        select(StudyGroupInvitation).where(StudyGroupInvitation.id == invitation_id)
    )
    invitation = result.scalars().first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.invited_user_id != user_id:
        raise HTTPException(status_code=403, detail="This invitation is not for you")

    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail=f"Invitation is {invitation.status}")

    if invitation.expires_at and invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")

    # Add as member
    service = get_study_group_service(db)
    existing = await db.execute(
        select(StudyGroupMember).where(
            StudyGroupMember.group_id == invitation.group_id,
            StudyGroupMember.user_id == user_id,
        )
    )
    if not existing.scalars().first():
        member = StudyGroupMember(
            group_id=invitation.group_id,
            user_id=user_id,
            role="member",
            joined_at=datetime.now(timezone.utc),
        )
        db.add(member)

    invitation.status = "accepted"
    invitation.accepted_at = datetime.now(timezone.utc)
    await db.commit()

    return await service.get_group(invitation.group_id)


@router.post("/invitations/{invitation_id}/decline")
async def decline_invitation(
    invitation_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Decline a pending study group invitation."""
    result = await db.execute(
        select(StudyGroupInvitation).where(StudyGroupInvitation.id == invitation_id)
    )
    invitation = result.scalars().first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.invited_user_id != user_id:
        raise HTTPException(status_code=403, detail="This invitation is not for you")

    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail=f"Invitation is {invitation.status}")

    invitation.status = "declined"
    await db.commit()
    return {"detail": "Invitation declined"}


# ============================================================
# Invitation Link management
# ============================================================


@router.post("/{group_id}/invite-link", response_model=InviteLinkOut)
async def generate_invite_link(
    group_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Generate or retrieve the invitation link for a group. Admin/Owner only."""
    service = get_study_group_service(db)
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Study group not found")

    # Check admin
    admin_check = await db.execute(
        select(StudyGroupMember).where(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == user_id,
            StudyGroupMember.status == "active",
        )
    )
    admin_member = admin_check.scalars().first()
    if not admin_member or admin_member.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Get or create token
    group_result = await db.execute(
        select(StudyGroup).where(StudyGroup.id == group_id)
    )
    db_group = group_result.scalars().first()
    if not db_group.invite_token:
        db_group.invite_token = generate_invite_token()
        await db.commit()

    frontend_base = _resolve_frontend_base(request)
    return InviteLinkOut(
        token=db_group.invite_token,
        link=f"{frontend_base}/study-groups/join/{db_group.invite_token}",
    )


@router.post("/{group_id}/invite-link/regenerate", response_model=InviteLinkOut)
async def regenerate_invite_link(
    group_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Regenerate the invitation link (invalidates old link). Admin/Owner only."""
    service = get_study_group_service(db)
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Study group not found")

    admin_check = await db.execute(
        select(StudyGroupMember).where(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == user_id,
            StudyGroupMember.status == "active",
        )
    )
    admin_member = admin_check.scalars().first()
    if not admin_member or admin_member.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    group_result = await db.execute(
        select(StudyGroup).where(StudyGroup.id == group_id)
    )
    db_group = group_result.scalars().first()
    db_group.invite_token = generate_invite_token()
    await db.commit()

    frontend_base = _resolve_frontend_base(request)
    return InviteLinkOut(
        token=db_group.invite_token,
        link=f"{frontend_base}/study-groups/join/{db_group.invite_token}",
    )


@router.post("/{group_id}/invite-link/revoke")
async def revoke_invite_link(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Revoke the invitation link. Admin/Owner only."""
    service = get_study_group_service(db)
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Study group not found")

    admin_check = await db.execute(
        select(StudyGroupMember).where(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == user_id,
            StudyGroupMember.status == "active",
        )
    )
    admin_member = admin_check.scalars().first()
    if not admin_member or admin_member.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    group_result = await db.execute(
        select(StudyGroup).where(StudyGroup.id == group_id)
    )
    db_group = group_result.scalars().first()
    db_group.invite_token = None
    await db.commit()

    return {"detail": "Invitation link revoked"}


# ============================================================
# Group Memory, Leaderboard, Achievements (existing - preserved)
# ============================================================


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
