"""
WebSocket Manager - Real-time bidirectional communication for Agent Studio.
Supports streaming LLM responses, run progress updates, and live collaboration.
"""

import uuid
import json
import asyncio
from typing import Optional, Dict, List, Any, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from backend.config.settings import settings


class WSMessageType(str, Enum):
    RUN_STARTED = "run_started"
    RUN_PROGRESS = "run_progress"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    LLM_TOKEN = "llm_token"
    LLM_COMPLETE = "llm_complete"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESPONSE = "approval_response"
    AGENT_STATUS = "agent_status"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WSMessage(BaseModel):
    """WebSocket message envelope."""
    type: WSMessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
    channel: str = "default"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])


class WSConnection(BaseModel):
    """Tracks a single WebSocket connection."""
    connection_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_id: str = ""
    tenant_id: str = ""
    channels: Set[str] = Field(default_factory=lambda: {"default"})
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_ping: Optional[datetime] = None
    message_count: int = 0

    class Config:
        arbitrary_types_allowed = True


class WebSocketManager:
    """
    Manages WebSocket connections for real-time streaming.
    Supports channel-based pub/sub for targeted message delivery.

    Usage with FastAPI:
        ws_manager = WebSocketManager()

        @app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await ws_manager.connect(client_id, websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    await ws_manager.handle_message(client_id, data)
            except WebSocketDisconnect:
                ws_manager.disconnect(client_id)
    """

    def __init__(self, max_connections: int = 100):
        self._connections: Dict[str, Any] = {}  # connection_id -> WebSocket object
        self._metadata: Dict[str, WSConnection] = {}  # connection_id -> metadata
        self._channels: Dict[str, Set[str]] = {"default": set()}  # channel -> set of connection_ids
        self._max_connections = max_connections

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    async def connect(
        self,
        connection_id: str,
        websocket: Any,
        user_id: str = "",
        tenant_id: str = "",
        channels: Optional[List[str]] = None,
    ) -> bool:
        """Register a new WebSocket connection."""
        if self.active_connections >= self._max_connections:
            return False

        self._connections[connection_id] = websocket
        meta = WSConnection(
            connection_id=connection_id,
            user_id=user_id,
            tenant_id=tenant_id,
            channels=set(channels or ["default"]),
        )
        self._metadata[connection_id] = meta

        for ch in meta.channels:
            if ch not in self._channels:
                self._channels[ch] = set()
            self._channels[ch].add(connection_id)

        # Send welcome message
        await self.send_to(connection_id, WSMessage(
            type=WSMessageType.AGENT_STATUS,
            payload={"status": "connected", "connection_id": connection_id},
        ))
        return True

    def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        self._connections.pop(connection_id, None)
        meta = self._metadata.pop(connection_id, None)
        if meta:
            for ch in meta.channels:
                if ch in self._channels:
                    self._channels[ch].discard(connection_id)

    async def send_to(self, connection_id: str, message: WSMessage) -> bool:
        """Send a message to a specific connection."""
        ws = self._connections.get(connection_id)
        if not ws:
            return False
        try:
            await ws.send_text(message.model_dump_json())
            meta = self._metadata.get(connection_id)
            if meta:
                meta.message_count += 1
            return True
        except Exception:
            self.disconnect(connection_id)
            return False

    async def broadcast_to_channel(self, channel: str, message: WSMessage) -> int:
        """Broadcast a message to all connections subscribed to a channel."""
        message.channel = channel
        conn_ids = self._channels.get(channel, set()).copy()
        sent = 0
        for cid in conn_ids:
            if await self.send_to(cid, message):
                sent += 1
        return sent

    async def broadcast_all(self, message: WSMessage) -> int:
        """Broadcast to all connected clients."""
        sent = 0
        for cid in list(self._connections.keys()):
            if await self.send_to(cid, message):
                sent += 1
        return sent

    async def stream_llm_tokens(
        self,
        connection_id: str,
        model_id: str,
        run_id: str,
        token_iterator: Any,
    ) -> Dict[str, Any]:
        """Stream LLM tokens to a WebSocket connection in real-time."""
        total_tokens = 0
        full_response = []

        async for chunk in token_iterator:
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            full_response.append(token)
            total_tokens += 1

            await self.send_to(connection_id, WSMessage(
                type=WSMessageType.LLM_TOKEN,
                payload={
                    "run_id": run_id,
                    "model_id": model_id,
                    "token": token,
                    "token_index": total_tokens,
                },
            ))

        await self.send_to(connection_id, WSMessage(
            type=WSMessageType.LLM_COMPLETE,
            payload={
                "run_id": run_id,
                "model_id": model_id,
                "total_tokens": total_tokens,
                "full_response": "".join(full_response),
            },
        ))

        return {"total_tokens": total_tokens, "response": "".join(full_response)}

    async def handle_message(self, connection_id: str, raw_data: str) -> None:
        """Handle an incoming WebSocket message from a client."""
        try:
            data = json.loads(raw_data)
            msg_type = data.get("type", "")

            if msg_type == "ping":
                meta = self._metadata.get(connection_id)
                if meta:
                    meta.last_ping = datetime.utcnow()
                await self.send_to(connection_id, WSMessage(type=WSMessageType.PONG))

            elif msg_type == "subscribe":
                channel = data.get("channel", "default")
                meta = self._metadata.get(connection_id)
                if meta:
                    meta.channels.add(channel)
                if channel not in self._channels:
                    self._channels[channel] = set()
                self._channels[channel].add(connection_id)

            elif msg_type == "unsubscribe":
                channel = data.get("channel", "default")
                meta = self._metadata.get(connection_id)
                if meta:
                    meta.channels.discard(channel)
                if channel in self._channels:
                    self._channels[channel].discard(connection_id)

        except json.JSONDecodeError:
            await self.send_to(connection_id, WSMessage(
                type=WSMessageType.ERROR,
                payload={"error": "Invalid JSON"},
            ))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_connections": self.active_connections,
            "max_connections": self._max_connections,
            "channels": {ch: len(ids) for ch, ids in self._channels.items()},
            "total_messages_sent": sum(m.message_count for m in self._metadata.values()),
        }
