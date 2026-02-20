"""
Webhook Handler - Inbound/outbound webhook management for Agent Studio.
Agents can be triggered via inbound webhooks and send results to outbound webhooks.
"""

import hmac
import hashlib
import uuid
import asyncio
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

import httpx

from backend.config.settings import settings


class WebhookDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class WebhookStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"


class WebhookConfig(BaseModel):
    """Configuration for a webhook endpoint."""
    webhook_id: str = Field(default_factory=lambda: f"WH-{uuid.uuid4().hex[:8].upper()}")
    name: str
    direction: WebhookDirection
    url: str = ""  # target URL for outbound; generated path for inbound
    secret: str = Field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: Optional[str] = None  # agent to trigger for inbound
    headers: Dict[str, str] = Field(default_factory=dict)
    payload_schema: Dict[str, Any] = Field(default_factory=dict)
    status: WebhookStatus = WebhookStatus.ACTIVE
    retry_count: int = 3
    retry_delay_seconds: int = 5
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WebhookEvent(BaseModel):
    """Record of a webhook invocation."""
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    webhook_id: str
    direction: WebhookDirection
    payload: Dict[str, Any] = Field(default_factory=dict)
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    latency_ms: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WebhookHandler:
    """
    Manages webhook registrations, signature verification, and delivery.
    """

    def __init__(self):
        self._webhooks: Dict[str, WebhookConfig] = {}
        self._events: List[WebhookEvent] = []
        self._handlers: Dict[str, Callable] = {}  # inbound webhook_id -> handler function

    def register(self, config: WebhookConfig) -> WebhookConfig:
        if config.direction == WebhookDirection.INBOUND:
            config.url = f"/webhooks/inbound/{config.webhook_id}"
        self._webhooks[config.webhook_id] = config
        return config

    def unregister(self, webhook_id: str) -> bool:
        return self._webhooks.pop(webhook_id, None) is not None

    def get(self, webhook_id: str) -> Optional[WebhookConfig]:
        return self._webhooks.get(webhook_id)

    def list_all(self) -> List[WebhookConfig]:
        return list(self._webhooks.values())

    def set_handler(self, webhook_id: str, handler: Callable) -> None:
        self._handlers[webhook_id] = handler

    def verify_signature(self, webhook_id: str, payload: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 signature for inbound webhooks."""
        config = self.get(webhook_id)
        if not config:
            return False
        expected = hmac.new(
            config.secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    async def handle_inbound(self, webhook_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process an inbound webhook payload."""
        config = self.get(webhook_id)
        if not config:
            return {"error": "Webhook not found"}
        if config.status != WebhookStatus.ACTIVE:
            return {"error": "Webhook is paused"}

        config.last_triggered = datetime.utcnow()
        config.trigger_count += 1

        event = WebhookEvent(
            webhook_id=webhook_id,
            direction=WebhookDirection.INBOUND,
            payload=payload,
        )

        handler = self._handlers.get(webhook_id)
        if handler:
            try:
                result = await handler(payload) if asyncio.iscoroutinefunction(handler) else handler(payload)
                event.success = True
                event.response_body = str(result)[:1000]
                self._events.append(event)
                return {"status": "processed", "event_id": event.event_id, "result": result}
            except Exception as e:
                event.error = str(e)
                self._events.append(event)
                return {"status": "error", "event_id": event.event_id, "error": str(e)}
        else:
            event.success = True
            event.response_body = "No handler registered; payload queued"
            self._events.append(event)
            return {"status": "queued", "event_id": event.event_id}

    async def send_outbound(self, webhook_id: str, payload: Dict[str, Any]) -> WebhookEvent:
        """Send an outbound webhook with retry logic."""
        config = self.get(webhook_id)
        if not config:
            raise ValueError(f"Webhook '{webhook_id}' not found")

        event = WebhookEvent(
            webhook_id=webhook_id,
            direction=WebhookDirection.OUTBOUND,
            payload=payload,
        )

        headers = {**config.headers, "Content-Type": "application/json"}
        # Add HMAC signature
        import json
        body = json.dumps(payload).encode()
        sig = hmac.new(config.secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={sig}"

        import time
        async with httpx.AsyncClient(timeout=30) as client:
            for attempt in range(config.retry_count):
                try:
                    start = time.time()
                    response = await client.post(config.url, json=payload, headers=headers)
                    event.latency_ms = round((time.time() - start) * 1000, 1)
                    event.response_status = response.status_code
                    event.response_body = response.text[:1000]
                    event.success = 200 <= response.status_code < 300

                    if event.success:
                        break
                except Exception as e:
                    event.error = str(e)
                    if attempt < config.retry_count - 1:
                        await asyncio.sleep(config.retry_delay_seconds)

        config.last_triggered = datetime.utcnow()
        config.trigger_count += 1
        self._events.append(event)
        return event

    def get_events(self, webhook_id: Optional[str] = None, limit: int = 50) -> List[WebhookEvent]:
        events = self._events
        if webhook_id:
            events = [e for e in events if e.webhook_id == webhook_id]
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
