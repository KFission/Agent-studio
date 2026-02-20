"""
LangGraph Client — Bridge between Agent Studio and LangGraph Supervisor Server.
Handles assistant CRUD, thread management, and chat execution via the LangGraph API.
"""

import os
import json
import logging
import httpx
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Model ID mapping: Agent Studio format → LangGraph supervisor format
MODEL_ID_MAP = {
    # OpenAI
    "gpt-4o": "openai:gpt-4o",
    "gpt-4o-mini": "openai:gpt-4o-mini",
    "gpt-4.1": "openai:gpt-4.1",
    "gpt-4.1-mini": "openai:gpt-4.1-mini",
    "o3": "openai:o3",
    "o3-mini": "openai:o3-mini",
    "o4-mini": "openai:o4-mini",
    # Anthropic
    "claude-sonnet-4": "anthropic:claude-sonnet-4-0",
    "claude-sonnet-4-20250514": "anthropic:claude-sonnet-4-0",
    "claude-3-7-sonnet": "anthropic:claude-3-7-sonnet-latest",
    "claude-3-5-sonnet": "anthropic:claude-3-5-sonnet-latest",
    "claude-3-5-haiku": "anthropic:claude-3-5-haiku-latest",
    "claude-3-5-haiku-20241022": "anthropic:claude-3-5-haiku-latest",
    # Google (Vertex AI — uses service account via GOOGLE_APPLICATION_CREDENTIALS)
    "gemini-2.5-flash": "google_vertexai:gemini-2.5-flash",
    "gemini-2.5-pro": "google_vertexai:gemini-2.5-pro",
    "gemini-2.0-flash": "google_vertexai:gemini-2.0-flash",
    "gemini-1.5-pro": "google_vertexai:gemini-1.5-pro",
    "gemini-1.5-flash": "google_vertexai:gemini-1.5-flash",
}

# Reverse mapping: LangGraph format → Agent Studio format
REVERSE_MODEL_MAP = {v: k for k, v in MODEL_ID_MAP.items()}

GRAPH_ID = "multi_agent_supervisor"


class LangGraphClient:
    """Client for interacting with the LangGraph Supervisor server."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("LANGGRAPH_URL", "http://localhost:2024")).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)
        logger.info(f"[LangGraph Client] Initialized with base_url={self.base_url}")

    # ── Health ────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Check if the LangGraph server is reachable."""
        try:
            resp = await self._client.get("/ok")
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"[LangGraph Client] Health check failed: {e}")
            return False

    # ── Model Mapping ─────────────────────────────────────────────

    @staticmethod
    def to_langgraph_model(agent_studio_model: str) -> str:
        """Convert Agent Studio model ID to LangGraph format."""
        if ":" in agent_studio_model:
            return agent_studio_model  # already in provider:model format
        return MODEL_ID_MAP.get(agent_studio_model, f"openai:{agent_studio_model}")

    @staticmethod
    def from_langgraph_model(langgraph_model: str) -> str:
        """Convert LangGraph model ID to Agent Studio format."""
        if langgraph_model in REVERSE_MODEL_MAP:
            return REVERSE_MODEL_MAP[langgraph_model]
        if ":" in langgraph_model:
            return langgraph_model.split(":", 1)[1]
        return langgraph_model

    # ── Assistants (Agents) CRUD ──────────────────────────────────

    async def create_assistant(
        self,
        name: str,
        system_prompt: str = "",
        model_id: str = "gemini-2.5-flash",
        description: str = "",
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Create an assistant on the LangGraph server."""
        config = {
            "configurable": {
                "system_prompt": system_prompt or "You are a helpful assistant.",
                "supervisor_model": self.to_langgraph_model(model_id),
                "agents": [],
            }
        }
        body = {
            "graph_id": GRAPH_ID,
            "name": name,
            "config": config,
            "metadata": {
                "description": description,
                "source": "agent_studio",
                **(metadata or {}),
            },
        }
        resp = await self._client.post("/assistants", json=body)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"[LangGraph Client] Created assistant: {data.get('assistant_id')} ({name})")
        return data

    async def update_assistant(
        self,
        assistant_id: str,
        name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        model_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Update an existing assistant on the LangGraph server."""
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name

        # Build config update
        configurable: Dict[str, Any] = {}
        if system_prompt is not None:
            configurable["system_prompt"] = system_prompt
        if model_id is not None:
            configurable["supervisor_model"] = self.to_langgraph_model(model_id)
        if configurable:
            body["config"] = {"configurable": configurable}

        if metadata is not None or description is not None:
            meta = metadata or {}
            if description is not None:
                meta["description"] = description
            meta["source"] = "agent_studio"
            body["metadata"] = meta

        resp = await self._client.patch(f"/assistants/{assistant_id}", json=body)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"[LangGraph Client] Updated assistant: {assistant_id}")
        return data

    async def get_assistant(self, assistant_id: str) -> Optional[Dict[str, Any]]:
        """Get an assistant by ID."""
        try:
            resp = await self._client.get(f"/assistants/{assistant_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"[LangGraph Client] Failed to get assistant {assistant_id}: {e}")
            return None

    async def delete_assistant(self, assistant_id: str) -> bool:
        """Delete an assistant."""
        try:
            resp = await self._client.delete(f"/assistants/{assistant_id}")
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.warning(f"[LangGraph Client] Failed to delete assistant {assistant_id}: {e}")
            return False

    async def list_assistants(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all assistants from the LangGraph server."""
        try:
            body = {"graph_id": GRAPH_ID, "limit": limit, "offset": 0}
            resp = await self._client.post("/assistants/search", json=body)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"[LangGraph Client] Failed to list assistants: {e}")
            return []

    # ── Threads ───────────────────────────────────────────────────

    async def create_thread(self, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new thread for a conversation."""
        body: Dict[str, Any] = {}
        if metadata:
            body["metadata"] = metadata
        resp = await self._client.post("/threads", json=body)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"[LangGraph Client] Created thread: {data.get('thread_id')}")
        return data

    async def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get a thread by ID."""
        try:
            resp = await self._client.get(f"/threads/{thread_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    async def get_thread_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get the current state of a thread (includes messages)."""
        try:
            resp = await self._client.get(f"/threads/{thread_id}/state")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    # ── Chat (Run) ────────────────────────────────────────────────

    async def chat(
        self,
        assistant_id: str,
        thread_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Send a message to an assistant and get a response.
        Uses the /runs/wait endpoint for synchronous execution.
        """
        body = {
            "assistant_id": assistant_id,
            "input": {
                "messages": [
                    {"role": "user", "content": message}
                ]
            },
        }
        resp = await self._client.post(
            f"/threads/{thread_id}/runs/wait",
            json=body,
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json()

    async def chat_stream(
        self,
        assistant_id: str,
        thread_id: str,
        message: str,
    ):
        """
        Send a message and stream the response.
        Yields SSE events from the LangGraph server.
        """
        body = {
            "assistant_id": assistant_id,
            "input": {
                "messages": [
                    {"role": "user", "content": message}
                ]
            },
            "stream_mode": ["messages"],
        }
        async with self._client.stream(
            "POST",
            f"/threads/{thread_id}/runs/stream",
            json=body,
            timeout=120.0,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.strip():
                    yield line

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()