"""
WebSocket endpoint for real-time study group chat.

Handles:
- Connection authentication via JWT query param
- Group membership verification
- Message broadcasting within group
- /mentora AI command detection
- Typing indicators
- Online presence
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_access_token
from app.database.database import AsyncSessionLocal
from app.models.study_group import StudyGroup, StudyGroupMember, StudyGroupMessage
from app.models.user import User
from app.websocket.manager import connection_manager
from app.services.study_group_service import StudyGroupService
from app.services.tutor_service import TutorService
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter()
tutor_service = TutorService()
memory_service = MemoryService()


async def _authenticate_ws(token: str) -> int | None:
    """Authenticate a WebSocket connection via JWT token. Returns user_id or None."""
    payload = await verify_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return int(user_id)


async def _is_group_member(db: AsyncSession, group_id: int, user_id: int) -> bool:
    """Check if a user is an active member of the given group."""
    result = await db.execute(
        select(StudyGroupMember).where(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == user_id,
            StudyGroupMember.status == "active",
        )
    )
    return result.scalars().first() is not None


async def _get_user_info(db: AsyncSession, user_id: int) -> dict:
    """Get user info for WebSocket events."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user:
        return {"id": user.id, "username": user.username, "full_name": user.full_name}
    return {"id": user_id, "username": "unknown", "full_name": None}


@router.websocket("/{group_id}/ws")
async def study_group_websocket(
    websocket: WebSocket,
    group_id: int,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time group chat.

    Query params:
        token: JWT access token for authentication

    Connects user to the group's real-time chat channel.
    Verifies authentication and group membership before accepting.
    """
    # 1. Authenticate
    user_id = await _authenticate_ws(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # 2. Verify group exists and user is a member
    async with AsyncSessionLocal() as db:
        group_result = await db.execute(
            select(StudyGroup).where(
                StudyGroup.id == group_id,
                StudyGroup.is_active == True,
            )
        )
        group = group_result.scalars().first()
        if not group:
            await websocket.close(code=4004, reason="Group not found")
            return

        if not await _is_group_member(db, group_id, user_id):
            await websocket.close(code=4003, reason="Not a member of this group")
            return

        user_info = await _get_user_info(db, user_id)

    # 3. Connect
    await connection_manager.connect(websocket, group_id, user_id)

    # Send current online users to the newly connected user
    online_ids = connection_manager.get_online_user_ids(group_id)
    await connection_manager.send_personal(
        user_id,
        group_id,
        {
            "type": "online_users",
            "data": {"user_ids": list(online_ids)},
        },
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await connection_manager.send_personal(
                    user_id,
                    group_id,
                    {"type": "error", "data": {"message": "Invalid JSON"}},
                )
                continue

            msg_type = data.get("type", "")

            if msg_type == "message":
                await _handle_chat_message(data, group_id, user_id, user_info, db_factory=AsyncSessionLocal)

            elif msg_type == "edit_message":
                await _handle_edit_message(data, group_id, user_id, user_info, db_factory=AsyncSessionLocal)

            elif msg_type == "delete_message":
                await _handle_delete_message(data, group_id, user_id, db_factory=AsyncSessionLocal)

            elif msg_type == "typing_start":
                await connection_manager.start_typing(group_id, user_id)

            elif msg_type == "typing_stop":
                await connection_manager.stop_typing(group_id, user_id)

            else:
                await connection_manager.send_personal(
                    user_id,
                    group_id,
                    {"type": "error", "data": {"message": f"Unknown event type: {msg_type}"}},
                )

    except WebSocketDisconnect:
        await connection_manager.disconnect(group_id, user_id)
    except Exception as e:
        logger.error("WebSocket error for user %s in group %s: %s", user_id, group_id, e)
        await connection_manager.disconnect(group_id, user_id)


async def _handle_chat_message(
    data: dict,
    group_id: int,
    user_id: int,
    user_info: dict,
    db_factory,
):
    """Process an incoming chat message, including /mentora commands."""
    content = data.get("content", "").strip()
    if not content:
        return

    reply_to_message_id = data.get("reply_to_message_id")

    async with db_factory() as db:
        service = StudyGroupService(db)

        # Handle /mentora command
        if content.lower().startswith("/mentora"):
            await _handle_mentora_command(
                content, group_id, user_id, user_info, db, service
            )
            return

        # Normalize reply_to_message_id
        if reply_to_message_id is not None:
            try:
                reply_to_message_id = int(reply_to_message_id)
            except (TypeError, ValueError):
                reply_to_message_id = None

        # Normal message: persist and broadcast
        msg = await service.send_message(
            user_id=user_id, group_id=group_id, content=content, message_type="user",
            reply_to_message_id=reply_to_message_id,
        )
        if msg:
            await connection_manager.broadcast_to_group(
                group_id,
                {
                    "type": "message",
                    "data": _message_to_ws_dict(msg, user_id, user_info),
                },
            )

        # Stop typing indicator for this user
        await connection_manager.stop_typing(group_id, user_id)


async def _handle_edit_message(
    data: dict,
    group_id: int,
    user_id: int,
    user_info: dict,
    db_factory,
):
    """Handle message edit via WebSocket."""
    message_id = data.get("message_id")
    new_content = data.get("content", "").strip()
    if not message_id or not new_content:
        return

    try:
        message_id = int(message_id)
    except (TypeError, ValueError):
        await connection_manager.send_personal(
            user_id,
            group_id,
            {"type": "error", "data": {"message": "Invalid message_id"}},
        )
        return

    try:
        async with db_factory() as db:
            service = StudyGroupService(db)
            result = await service.edit_message(
                user_id=user_id, group_id=group_id, message_id=message_id, new_content=new_content
            )
            if result:
                await connection_manager.broadcast_to_group(
                    group_id,
                    {
                        "type": "message_edited",
                        "data": _message_to_ws_dict(result, user_id, user_info),
                    },
                )
            else:
                await connection_manager.send_personal(
                    user_id,
                    group_id,
                    {"type": "error", "data": {"message": "Cannot edit this message"}},
                )
    except Exception as e:
        logger.error("Edit message error for user %s in group %s: %s", user_id, group_id, e)
        await connection_manager.send_personal(
            user_id,
            group_id,
            {"type": "error", "data": {"message": "Failed to edit message"}},
        )


async def _handle_delete_message(
    data: dict,
    group_id: int,
    user_id: int,
    db_factory,
):
    """Handle message delete via WebSocket."""
    message_id = data.get("message_id")
    if not message_id:
        return

    try:
        message_id = int(message_id)
    except (TypeError, ValueError):
        await connection_manager.send_personal(
            user_id,
            group_id,
            {"type": "error", "data": {"message": "Invalid message_id"}},
        )
        return

    try:
        async with db_factory() as db:
            service = StudyGroupService(db)
            result = await service.delete_message(
                user_id=user_id, group_id=group_id, message_id=message_id
            )
            if result:
                await connection_manager.broadcast_to_group(
                    group_id,
                    {
                        "type": "message_deleted",
                        "data": _message_to_ws_dict(result),
                    },
                )
            else:
                await connection_manager.send_personal(
                    user_id,
                    group_id,
                    {"type": "error", "data": {"message": "Cannot delete this message"}},
                )
    except Exception as e:
        logger.error("Delete message error for user %s in group %s: %s", user_id, group_id, e)
        await connection_manager.send_personal(
            user_id,
            group_id,
            {"type": "error", "data": {"message": "Failed to delete message"}},
        )


def _message_to_ws_dict(msg, sender_user_id=None, sender_info=None):
    """Convert a StudyGroupMessageOut to a WebSocket broadcast dict."""
    data = {
        "id": msg.id,
        "group_id": msg.group_id,
        "sender": {
            "id": msg.sender_id,
            "username": sender_info["username"] if sender_info and sender_info.get("id") == sender_user_id else None,
            "full_name": sender_info["full_name"] if sender_info and sender_info.get("id") == sender_user_id else msg.sender_name,
        },
        "message": msg.content,
        "message_type": msg.message_type,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
        "deleted_at": msg.deleted_at.isoformat() if msg.deleted_at else None,
        "is_deleted": msg.is_deleted,
        "reply_to": msg.reply_to.model_dump() if isinstance(msg.reply_to, BaseModel) else msg.reply_to,
        "forwarded_from": msg.forwarded_from.model_dump() if isinstance(msg.forwarded_from, BaseModel) else msg.forwarded_from,
    }
    return data


async def _handle_mentora_command(
    content: str,
    group_id: int,
    user_id: int,
    user_info: dict,
    db: AsyncSession,
    service: StudyGroupService,
):
    """Handle /mentora AI tutor command within group chat."""
    prompt = content[len("/mentora"):].strip()

    # Broadcast a "system" event so clients know AI is processing
    await connection_manager.broadcast_to_group(
        group_id,
        {
            "type": "ai_typing",
            "data": {"user_id": user_id, "username": user_info["username"]},
        },
    )

    if not prompt:
        # Save user's empty command and AI hint
        user_msg = await service.send_message(
            user_id=user_id, group_id=group_id, content=content, message_type="user"
        )
        if user_msg:
            await connection_manager.broadcast_to_group(
                group_id,
                {"type": "message", "data": _message_to_ws_dict(user_msg, user_id, user_info)},
            )

        ai_msg = await service.save_ai_message(
            group_id=group_id,
            content="Please provide a question after /mentora. For example: /mentora explain RAG",
        )
        await connection_manager.broadcast_to_group(
            group_id,
            {"type": "ai_response", "data": _message_to_ws_dict(ai_msg, None, {"id": None, "username": "Mentora AI", "full_name": "Mentora AI"})},
        )
        return

    # Build context
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

    # Save user's command
    user_msg = await service.send_message(
        user_id=user_id, group_id=group_id, content=content, message_type="user"
    )
    if user_msg:
        await connection_manager.broadcast_to_group(
            group_id,
            {"type": "message", "data": _message_to_ws_dict(user_msg, user_id, user_info)},
        )

    # Save and broadcast AI response
    ai_msg = await service.save_ai_message(group_id=group_id, content=ai_response)
    await connection_manager.broadcast_to_group(
        group_id,
        {"type": "ai_response", "data": _message_to_ws_dict(ai_msg, None, {"id": None, "username": "Mentora AI", "full_name": "Mentora AI"})},
    )

    # Extract and update group memory (non-blocking)
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

    # Stop typing indicator for this user
    await connection_manager.stop_typing(group_id, user_id)
