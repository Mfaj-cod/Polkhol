from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, group_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[group_id].add(websocket)

    def disconnect(self, group_id: int, websocket: WebSocket) -> None:
        if group_id in self._connections:
            self._connections[group_id].discard(websocket)
            if not self._connections[group_id]:
                self._connections.pop(group_id, None)

    async def broadcast(self, group_id: int, payload: dict) -> None:
        websockets = list(self._connections.get(group_id, set()))
        for websocket in websockets:
            await websocket.send_json(payload)


