"""
JAI Agent OS — DB-backed API Routes
Persistent agent CRUD, credential management, and agent invocation.
These routes use PostgreSQL via SQLAlchemy async, replacing the in-memory registry.
"""

import logging
from typing import Optional, List

from fastapi import HTTPException, Query, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.engine import get_db_session
from backend.db.agent_repository import AgentRepository
from backend.db.credential_store import CredentialStore
from backend.agent_service.agent_registry import (
    AgentDefinition, AgentStatus, ModelConfig, RAGConfig,
    MemoryConfig, AccessControl,
)

logger = logging.getLogger(__name__)


# ── Request Models ────────────────────────────────────────────────

class CreateAgentDBRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    model_config_: dict = Field(default_factory=dict, alias="model_config")
    context: str = ""
    rag_enabled: bool = False
    memory_enabled: bool = True
    owner_id: str = ""
    credential_id: Optional[str] = None


class UpdateAgentDBRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    model_config_: Optional[dict] = Field(default=None, alias="model_config")
    context: Optional[str] = None
    status: Optional[str] = None
    credential_id: Optional[str] = None


class UploadCredentialRequest(BaseModel):
    name: str
    provider: str  # "google", "anthropic", "openai"
    credential_json: dict  # The raw secret (e.g. full service account JSON)
    display_metadata: Optional[dict] = None


class InvokeAgentRequest(BaseModel):
    message: str
    session_id: str = "default"
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


# ── Route Registration ───────────────────────────────────────────

def register_db_routes(app_router, provider_factory):
    """Register DB-backed routes onto the FastAPI app."""

    # ══════════════════════════════════════════════════════════════
    # CREDENTIALS (encrypted at rest)
    # ══════════════════════════════════════════════════════════════

    @app_router.post("/credentials")
    async def upload_credential(
        req: UploadCredentialRequest,
        db: AsyncSession = Depends(get_db_session),
    ):
        """Upload and encrypt a provider credential (e.g. Vertex AI service account JSON)."""
        store = CredentialStore(db)
        try:
            result = await store.store(
                name=req.name,
                provider=req.provider,
                credential_data=req.credential_json,
                display_metadata=req.display_metadata,
            )
            return {"status": "stored", **result}
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app_router.get("/credentials")
    async def list_credentials(
        provider: Optional[str] = None,
        db: AsyncSession = Depends(get_db_session),
    ):
        """List all credentials (metadata only — secrets are never returned)."""
        store = CredentialStore(db)
        creds = await store.list_all(provider)
        return {"count": len(creds), "credentials": creds}

    @app_router.get("/credentials/{credential_id}")
    async def get_credential(
        credential_id: str,
        db: AsyncSession = Depends(get_db_session),
    ):
        """Get credential metadata (no secret data)."""
        store = CredentialStore(db)
        meta = await store.get_metadata(credential_id)
        if not meta:
            raise HTTPException(404, "Credential not found")
        return meta

    @app_router.delete("/credentials/{credential_id}")
    async def deactivate_credential(
        credential_id: str,
        db: AsyncSession = Depends(get_db_session),
    ):
        """Soft-delete a credential."""
        store = CredentialStore(db)
        if not await store.deactivate(credential_id):
            raise HTTPException(404, "Credential not found")
        return {"status": "deactivated"}

    # ══════════════════════════════════════════════════════════════
    # AGENTS (DB-backed CRUD)
    # ══════════════════════════════════════════════════════════════

    @app_router.post("/db/agents")
    async def create_agent_db(
        req: CreateAgentDBRequest,
        db: AsyncSession = Depends(get_db_session),
    ):
        """Create a new agent persisted to PostgreSQL."""
        mc = ModelConfig(**req.model_config_) if req.model_config_ else ModelConfig()
        agent = AgentDefinition(
            name=req.name,
            description=req.description,
            tags=req.tags,
            model_config=mc,
            rag_config=RAGConfig(enabled=req.rag_enabled),
            memory_config=MemoryConfig(
                short_term_enabled=req.memory_enabled,
                long_term_enabled=req.memory_enabled,
            ),
            context=req.context,
            access_control=AccessControl(owner_id=req.owner_id),
        )
        repo = AgentRepository(db)
        created = await repo.create(agent, credential_id=req.credential_id)
        return {"status": "created", "agent_id": created.agent_id}

    @app_router.get("/db/agents")
    async def list_agents_db(
        status: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = Query(default=100, le=500),
        offset: int = 0,
        db: AsyncSession = Depends(get_db_session),
    ):
        """List agents from PostgreSQL."""
        repo = AgentRepository(db)
        s = AgentStatus(status) if status else None
        agents = await repo.list_all(s, owner_id, limit, offset)
        return {
            "count": len(agents),
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "description": a.description,
                    "status": a.status.value,
                    "version": a.version,
                    "tags": a.tags,
                    "model": a.model_config_.model_id,
                    "updated_at": a.updated_at.isoformat(),
                }
                for a in agents
            ],
        }

    @app_router.get("/db/agents/{agent_id}")
    async def get_agent_db(
        agent_id: str,
        db: AsyncSession = Depends(get_db_session),
    ):
        """Get a single agent by ID from PostgreSQL."""
        repo = AgentRepository(db)
        agent = await repo.get(agent_id)
        if not agent:
            raise HTTPException(404, "Agent not found")
        return agent.model_dump(mode="json", by_alias=True)

    @app_router.put("/db/agents/{agent_id}")
    async def update_agent_db(
        agent_id: str,
        req: UpdateAgentDBRequest,
        db: AsyncSession = Depends(get_db_session),
    ):
        """Update an agent in PostgreSQL."""
        updates = {}
        if req.name is not None:
            updates["name"] = req.name
        if req.description is not None:
            updates["description"] = req.description
        if req.tags is not None:
            updates["tags"] = req.tags
        if req.model_config_ is not None:
            updates["model_config_"] = ModelConfig(**req.model_config_)
        if req.context is not None:
            updates["context"] = req.context
        if req.status is not None:
            updates["status"] = AgentStatus(req.status)

        repo = AgentRepository(db)
        agent = await repo.update(agent_id, updates, credential_id=req.credential_id)
        if not agent:
            raise HTTPException(404, "Agent not found")
        return {"status": "updated", "agent_id": agent.agent_id, "version": agent.version}

    @app_router.delete("/db/agents/{agent_id}")
    async def delete_agent_db(
        agent_id: str,
        db: AsyncSession = Depends(get_db_session),
    ):
        """Delete an agent from PostgreSQL."""
        repo = AgentRepository(db)
        if not await repo.delete(agent_id):
            raise HTTPException(404, "Agent not found")
        return {"status": "deleted"}

    @app_router.get("/db/agents/stats/summary")
    async def agent_stats_db(
        db: AsyncSession = Depends(get_db_session),
    ):
        """Get agent stats from PostgreSQL."""
        repo = AgentRepository(db)
        return await repo.get_stats()

    # ══════════════════════════════════════════════════════════════
    # AGENT INVOCATION (end-to-end LLM call)
    # ══════════════════════════════════════════════════════════════

    @app_router.post("/db/agents/{agent_id}/invoke")
    async def invoke_agent(
        agent_id: str,
        req: InvokeAgentRequest,
        db: AsyncSession = Depends(get_db_session),
    ):
        """
        Invoke an agent — sends a message through the agent's configured LLM
        using stored credentials. Returns the LLM response.
        """
        repo = AgentRepository(db)
        cred_store = CredentialStore(db)

        # 1. Load agent + credential reference
        agent_data = await repo.get_with_credential_id(agent_id)
        if not agent_data:
            raise HTTPException(404, "Agent not found")

        agent: AgentDefinition = agent_data["agent"]
        credential_id: Optional[str] = agent_data["credential_id"]

        # 2. Resolve model config
        model_id = agent.model_config_.model_id
        temperature = req.temperature if req.temperature is not None else agent.model_config_.temperature
        max_tokens = req.max_tokens or agent.model_config_.max_tokens

        # 3. Load decrypted credentials if present
        credential_data = None
        if credential_id:
            credential_data = await cred_store.get_decrypted(credential_id)
            if not credential_data:
                raise HTTPException(400, f"Credential '{credential_id}' not found or inactive")

        # 4. Build system message from agent context
        messages = []
        if agent.context:
            messages.append({"role": "system", "content": agent.context})
        messages.append({"role": "user", "content": req.message})

        # 5. Create LLM and invoke
        try:
            import time
            llm = provider_factory.create(
                model_id=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                credential_data=credential_data,
            )

            # Convert to LangChain message format
            from langchain_core.messages import HumanMessage, SystemMessage
            lc_messages = []
            for m in messages:
                if m["role"] == "system":
                    lc_messages.append(SystemMessage(content=m["content"]))
                else:
                    lc_messages.append(HumanMessage(content=m["content"]))

            start = time.time()
            response = await llm.ainvoke(lc_messages)
            latency_ms = (time.time() - start) * 1000

            content = response.content if hasattr(response, "content") else str(response)
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

            return {
                "agent_id": agent_id,
                "model": model_id,
                "response": content,
                "latency_ms": round(latency_ms, 1),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "session_id": req.session_id,
            }
        except Exception as e:
            logger.error(f"Agent invocation failed for {agent_id}: {e}")
            raise HTTPException(500, f"Invocation failed: {str(e)}")
