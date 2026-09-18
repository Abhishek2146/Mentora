"""
WebSocket Connection Manager for Study Group real-time chat.

Manages per-group connections, online presence, and typing indicators.
"""

import json
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by study group."""

    def __init__(self):
        # group_id -> {user_id: WebSocket}
        self._connections: Dict[int, Dict[int, WebSocket]] = {}
        # group_id -> set of user_ids currently typing
        self._typing: Dict[int, Set[int]] = {}

    async def connect(self, websocket: WebSocket, group_id: int, user_id: int):
        """Accept a WebSocket connection and register it for a group."""
        await websocket.accept()
        if group_id not in self._connections:
            self._connections[group_id] = {}
        self._connections[group_id][user_id] = websocket

        # Broadcast user_online to other members in the group
        await self._broadcast_to_group(
            group_id,
            {
                "type": "user_online",
                "data": {"user_id": user_id},
            },
            exclude_user=user_id,
        )
        logger.info("User %s connected to group %s WS", user_id, group_id)

    async def disconnect(self, group_id: int, user_id: int):
        """Remove a WebSocket connection."""
        if group_id in self._connections:
            self._connections[group_id].pop(user_id, None)
            if not self._connections[group_id]:
                del self._connections[group_id]

        # Remove from typing
        if group_id in self._typing:
            self._typing[group_id].discard(user_id)
            if not self._typing[group_id]:
                del self._typing[group_id]

        # Broadcast user_offline
        await self._broadcast_to_group(
            group_id,
            {
                "type": "user_offline",
                "data": {"user_id": user_id},
            },
            exclude_user=user_id,
        )
        logger.info("User %s disconnected from group %s WS", user_id, group_id)

    async def send_personal(self, user_id: int, group_id: int, message: dict):
        """Send a message to a specific user in a group."""
        ws = self._connections.get(group_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("Failed to send to user %s in group %s", user_id, group_id)

    async def broadcast_to_group(self, group_id: int, message: dict, exclude_user: Optional[int] = None):
        """Broadcast a message to all connected members of a group."""
        await self._broadcast_to_group(group_id, message, exclude_user=exclude_user)

    async def _broadcast_to_group(self, group_id: int, message: dict, exclude_user: Optional[int] = None):
        """Internal broadcast method."""
        connections = self._connections.get(group_id, {})
        disconnected = []
        for uid, ws in connections.items():
            if uid == exclude_user:
                continue
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to send to user %s in group %s: %s", uid, group_id, e
                )
                disconnected.append(uid)
        for uid in disconnected:
            connections.pop(uid, None)

    def get_online_user_ids(self, group_id: int) -> Set[int]:
        """Get set of online user IDs for a group."""
        return set(self._connections.get(group_id, {}).keys())

    def is_user_online(self, group_id: int, user_id: int) -> bool:
        """Check if a user is online in a group."""
        return user_id in self._connections.get(group_id, {})

    async def start_typing(self, group_id: int, user_id: int):
        """Mark a user as typing and broadcast to others."""
        if group_id not in self._typing:
            self._typing[group_id] = set()
        self._typing[group_id].add(user_id)
        await self._broadcast_to_group(
            group_id,
            {
                "type": "typing_start",
                "data": {"user_id": user_id},
            },
            exclude_user=user_id,
        )

    async def stop_typing(self, group_id: int, user_id: int):
        """Remove a user from typing and broadcast to others."""
        if group_id in self._typing:
            self._typing[group_id].discard(user_id)
        await self._broadcast_to_group(
            group_id,
            {
                "type": "typing_stop",
                "data": {"user_id": user_id},
            },
            exclude_user=user_id,
        )

    def get_typing_users(self, group_id: int) -> Set[int]:
        """Get set of user IDs currently typing in a group."""
        return self._typing.get(group_id, set()).copy()


# Singleton instance
connection_manager = ConnectionManager()
