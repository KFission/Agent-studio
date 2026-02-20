"""
JAI Agent OS — LangGraph Integration Routes
Bridges Agent Studio with the LangGraph Supervisor server on port 2024.
Provides endpoints for:
  - Syncing agent CRUD to LangGraph assistants
  - Listing LangGraph assistants for the Playground dropdown
  - Chat execution via LangGraph threads/runs
"""

import logging
import time
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

from backend.langgraph_client.client import LangGraphClient

logger = logging.getLogger(__name__)


# ── Request Models ────────────────────────────────────────────────

class CreateLangGraphAgentRequest(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = ""
    model_id: str = "gemini-2.5-flash"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateLangGraphAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LangGraphChatRequest(BaseModel):
    message: str
    assistant_id: str
    thread_id: Optional[str] = None


# ── Route Registration ────────────────────────────────────────────

def register_langgraph_routes(app, langgraph_client: LangGraphClient):
    """Register all LangGraph integration routes."""

    # ══════════════════════════════════════════════════════════════
    # HEALTH
    # ══════════════════════════════════════════════════════════════

    @app.get("/langgraph/health")
    async def langgraph_health():
        """Check if the LangGraph server is reachable."""
        healthy = await langgraph_client.health_check()
        return {
            "status": "ok" if healthy else "unreachable",
            "langgraph_url": langgraph_client.base_url,
        }

    # ══════════════════════════════════════════════════════════════
    # ASSISTANTS (LangGraph Agents)
    # ══════════════════════════════════════════════════════════════

    @app.get("/langgraph/assistants")
    async def list_langgraph_assistants(limit: int = Query(default=100, le=500)):
        """List all assistants from the LangGraph server."""
        try:
            assistants = await langgraph_client.list_assistants(limit=limit)
            # Normalize the response for the frontend
            result = []
            for a in assistants:
                cfg = (a.get("config") or {}).get("configurable") or {}
                meta = a.get("metadata") or {}
                model_lg = cfg.get("supervisor_model", "openai:gpt-4.1")
                result.append({
                    "assistant_id": a.get("assistant_id"),
                    "name": a.get("name", "Unnamed"),
                    "description": meta.get("description", ""),
                    "model": LangGraphClient.from_langgraph_model(model_lg),
                    "model_langgraph": model_lg,
                    "system_prompt": cfg.get("system_prompt", ""),
                    "agents": cfg.get("agents", []),
                    "graph_id": a.get("graph_id"),
                    "created_at": a.get("created_at"),
                    "updated_at": a.get("updated_at"),
                    "metadata": meta,
                    "source": "langgraph",
                })
            return {"count": len(result), "assistants": result}
        except Exception as e:
            logger.error(f"[LangGraph] Failed to list assistants: {e}")
            raise HTTPException(502, f"LangGraph server error: {str(e)}")

    @app.post("/langgraph/assistants")
    async def create_langgraph_assistant(req: CreateLangGraphAgentRequest):
        """Create a new assistant on the LangGraph server."""
        try:
            data = await langgraph_client.create_assistant(
                name=req.name,
                system_prompt=req.system_prompt,
                model_id=req.model_id,
                description=req.description,
                metadata={**req.metadata, "tags": req.tags},
            )
            return {
                "status": "created",
                "assistant_id": data.get("assistant_id"),
                "name": data.get("name"),
                "graph_id": data.get("graph_id"),
            }
        except Exception as e:
            logger.error(f"[LangGraph] Failed to create assistant: {e}")
            raise HTTPException(502, f"LangGraph server error: {str(e)}")

    @app.get("/langgraph/assistants/{assistant_id}")
    async def get_langgraph_assistant(assistant_id: str):
        """Get a specific assistant from the LangGraph server."""
        data = await langgraph_client.get_assistant(assistant_id)
        if not data:
            raise HTTPException(404, "Assistant not found on LangGraph server")
        cfg = (data.get("config") or {}).get("configurable") or {}
        meta = data.get("metadata") or {}
        model_lg = cfg.get("supervisor_model", "openai:gpt-4.1")
        return {
            "assistant_id": data.get("assistant_id"),
            "name": data.get("name", "Unnamed"),
            "description": meta.get("description", ""),
            "model": LangGraphClient.from_langgraph_model(model_lg),
            "model_langgraph": model_lg,
            "system_prompt": cfg.get("system_prompt", ""),
            "agents": cfg.get("agents", []),
            "graph_id": data.get("graph_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "metadata": meta,
        }

    @app.patch("/langgraph/assistants/{assistant_id}")
    async def update_langgraph_assistant(assistant_id: str, req: UpdateLangGraphAgentRequest):
        """Update an assistant on the LangGraph server."""
        try:
            data = await langgraph_client.update_assistant(
                assistant_id=assistant_id,
                name=req.name,
                system_prompt=req.system_prompt,
                model_id=req.model_id,
                description=req.description,
                metadata=req.metadata,
            )
            return {
                "status": "updated",
                "assistant_id": data.get("assistant_id"),
            }
        except Exception as e:
            logger.error(f"[LangGraph] Failed to update assistant: {e}")
            raise HTTPException(502, f"LangGraph server error: {str(e)}")

    @app.delete("/langgraph/assistants/{assistant_id}")
    async def delete_langgraph_assistant(assistant_id: str):
        """Delete an assistant from the LangGraph server."""
        success = await langgraph_client.delete_assistant(assistant_id)
        if not success:
            raise HTTPException(404, "Assistant not found or could not be deleted")
        return {"status": "deleted", "assistant_id": assistant_id}

    # ══════════════════════════════════════════════════════════════
    # CHAT (via LangGraph Threads + Runs)
    # ══════════════════════════════════════════════════════════════

    @app.post("/langgraph/chat")
    async def langgraph_chat(req: LangGraphChatRequest):
        """
        Send a message to a LangGraph assistant and get a response.
        Creates a new thread if thread_id is not provided.
        """
        start_time = time.time()

        try:
            # Create thread if not provided
            thread_id = req.thread_id
            if not thread_id:
                thread = await langgraph_client.create_thread(
                    metadata={"assistant_id": req.assistant_id}
                )
                thread_id = thread["thread_id"]

            # Execute the chat
            result = await langgraph_client.chat(
                assistant_id=req.assistant_id,
                thread_id=thread_id,
                message=req.message,
            )

            # Extract the assistant's response from the result
            response_content = ""
            messages = result.get("messages", [])
            if messages:
                # Get the last assistant message with non-empty content
                for msg in reversed(messages):
                    role = msg.get("role") or msg.get("type", "")
                    if role in ("assistant", "ai"):
                        content = msg.get("content", "")
                        if isinstance(content, list):
                            # Handle structured content (e.g., tool calls + text)
                            text_parts = [
                                p.get("text", "") for p in content
                                if isinstance(p, dict) and p.get("type") == "text"
                            ]
                            extracted = "\n".join(text_parts) if text_parts else ""
                            if extracted.strip():
                                response_content = extracted
                                break
                        elif isinstance(content, str) and content.strip():
                            response_content = content
                            break
                        # If content is empty, skip and check earlier messages

            elapsed_ms = round((time.time() - start_time) * 1000, 1)

            return {
                "response": response_content or "No response from agent.",
                "thread_id": thread_id,
                "assistant_id": req.assistant_id,
                "latency_ms": elapsed_ms,
                "messages": messages,
            }

        except Exception as e:
            logger.error(f"[LangGraph] Chat failed: {e}")
            raise HTTPException(502, f"LangGraph chat error: {str(e)}")

    @app.post("/langgraph/threads")
    async def create_langgraph_thread(assistant_id: Optional[str] = None):
        """Create a new conversation thread."""
        try:
            metadata = {}
            if assistant_id:
                metadata["assistant_id"] = assistant_id
            thread = await langgraph_client.create_thread(metadata=metadata)
            return {
                "status": "created",
                "thread_id": thread["thread_id"],
            }
        except Exception as e:
            logger.error(f"[LangGraph] Failed to create thread: {e}")
            raise HTTPException(502, f"LangGraph server error: {str(e)}")

    @app.get("/langgraph/threads/{thread_id}/state")
    async def get_langgraph_thread_state(thread_id: str):
        """Get the current state (messages) of a thread."""
        state = await langgraph_client.get_thread_state(thread_id)
        if not state:
            raise HTTPException(404, "Thread not found")
        return state

    # ══════════════════════════════════════════════════════════════
    # EXTERNAL API — Invoke a LangGraph agent programmatically
    # ══════════════════════════════════════════════════════════════

    class InvokeAgentRequest(BaseModel):
        message: str
        thread_id: Optional[str] = None

    @app.post("/langgraph/agents/{assistant_id}/invoke")
    async def invoke_langgraph_agent(assistant_id: str, req: InvokeAgentRequest):
        """
        Invoke a LangGraph agent via API.
        Creates a new thread if thread_id is not provided.
        Returns the agent's response along with thread_id for follow-up calls.

        Example:
            POST /langgraph/agents/{assistant_id}/invoke
            {"message": "Hello, what can you do?"}

        Follow-up (same conversation):
            POST /langgraph/agents/{assistant_id}/invoke
            {"message": "Tell me more", "thread_id": "<thread_id from previous response>"}
        """
        start_time = time.time()

        # Verify assistant exists
        assistant = await langgraph_client.get_assistant(assistant_id)
        if not assistant:
            raise HTTPException(404, f"Agent (assistant) '{assistant_id}' not found on LangGraph server")

        try:
            # Create thread if not provided
            thread_id = req.thread_id
            if not thread_id:
                thread = await langgraph_client.create_thread(
                    metadata={"assistant_id": assistant_id}
                )
                thread_id = thread["thread_id"]

            # Execute the chat
            result = await langgraph_client.chat(
                assistant_id=assistant_id,
                thread_id=thread_id,
                message=req.message,
            )

            # Extract the assistant's response
            response_content = ""
            messages = result.get("messages", [])
            if messages:
                for msg in reversed(messages):
                    role = msg.get("role") or msg.get("type", "")
                    if role in ("assistant", "ai"):
                        content = msg.get("content", "")
                        if isinstance(content, list):
                            text_parts = [
                                p.get("text", "") for p in content
                                if isinstance(p, dict) and p.get("type") == "text"
                            ]
                            extracted = "\n".join(text_parts) if text_parts else ""
                            if extracted.strip():
                                response_content = extracted
                                break
                        elif isinstance(content, str) and content.strip():
                            response_content = content
                            break
                        # If content is empty, skip and check earlier messages

            elapsed_ms = round((time.time() - start_time) * 1000, 1)

            return {
                "response": response_content or "No response from agent.",
                "assistant_id": assistant_id,
                "assistant_name": assistant.get("name", ""),
                "thread_id": thread_id,
                "latency_ms": elapsed_ms,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[LangGraph] Invoke failed for {assistant_id}: {e}")
            raise HTTPException(502, f"LangGraph invoke error: {str(e)}")
