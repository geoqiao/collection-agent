"""WebSocket connection manager for real-time simulation."""

from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    """Manage WebSocket connections per user."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast(self, message: dict, user_id: str) -> None:
        conns = self._connections.get(user_id, [])
        for ws in conns:
            await ws.send_json(message)
