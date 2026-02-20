"""
Agent Registry — Central registry for Agent-as-a-Service.
Each agent is a self-contained unit with its own model config, RAG,
memory, tools, DB connections, prompt context, and access controls.
Follows OAP patterns: Agent extends Assistant with deployment context.
DB-backed with in-memory cache for fast reads.
"""

import uuid
import copy
import logging
from typing import Optional, Dict, List, Any, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPLOYED = "deployed"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ModelConfig(BaseModel):
    """LLM configuration for an agent."""
    model_id: str = "gemini-2.5-flash"
    temperature: float = 0.0
    max_tokens: int = 4096
    system_prompt: str = ""
    fallback_model_id: Optional[str] = None


class RAGConfig(BaseModel):
    """Per-agent RAG configuration."""
    enabled: bool = False
    collection_ids: List[str] = Field(default_factory=list)
    embedding_model: str = "text-embedding-004"
    top_k: int = 5
    score_threshold: float = 0.7
    namespace: str = "default"


class MemoryConfig(BaseModel):
    """Per-agent memory configuration."""
    short_term_enabled: bool = True
    long_term_enabled: bool = True
    short_term_max_messages: int = 50
    long_term_store: str = "local"  # local, redis, postgres
    summarize_after: int = 20


class DBConfig(BaseModel):
    """Per-agent database access configuration."""
    structured_enabled: bool = False
    structured_type: str = "postgres"  # postgres, snowflake
    structured_connection_id: Optional[str] = None
    unstructured_enabled: bool = False
    unstructured_type: str = "pinecone"  # pinecone, chromadb
    unstructured_connection_id: Optional[str] = None
    allowed_tables: List[str] = Field(default_factory=list)
    read_only: bool = True


class ToolBinding(BaseModel):
    """A tool bound to an agent."""
    tool_id: str
    tool_name: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentEndpoint(BaseModel):
    """REST API endpoint configuration for Agent-as-a-Service."""
    enabled: bool = True
    path_prefix: str = ""  # auto-generated from agent_id
    rate_limit_rpm: int = 60
    require_api_key: bool = True
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])


class AccessControl(BaseModel):
    """Per-agent access control."""
    owner_id: str = ""
    allowed_users: Set[str] = Field(default_factory=set)
    allowed_roles: Set[str] = Field(default_factory=set)
    is_public: bool = False
    require_approval: bool = False


class AgentDefinition(BaseModel):
    """
    Complete agent definition — a self-contained agent unit.
    Each agent has its own model, RAG, memory, tools, DB access,
    prompt context, and access controls.
    """
    agent_id: str = Field(default_factory=lambda: f"agt-{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    version: int = 1
    status: AgentStatus = AgentStatus.DRAFT
    tags: List[str] = Field(default_factory=list)

    # Core configuration
    model_config_: ModelConfig = Field(default_factory=ModelConfig, alias="model_config")
    prompt_template_id: Optional[str] = None
    context: str = ""  # additional context injected into every call

    # Per-agent features
    rag_config: RAGConfig = Field(default_factory=RAGConfig)
    memory_config: MemoryConfig = Field(default_factory=MemoryConfig)
    db_config: DBConfig = Field(default_factory=DBConfig)
    tools: List[ToolBinding] = Field(default_factory=list)

    # Serving
    endpoint: AgentEndpoint = Field(default_factory=AgentEndpoint)
    access_control: AccessControl = Field(default_factory=AccessControl)

    # Graph reference (optional — links to visual canvas graph)
    graph_manifest_id: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class AgentRegistry:
    """
    Central registry for all agents. Provides CRUD, versioning,
    deployment lifecycle, and search.
    Uses an in-memory cache for fast reads, writes through to PostgreSQL.
    """

    def __init__(self):
        self._agents: Dict[str, AgentDefinition] = {}
        self._versions: Dict[str, List[AgentDefinition]] = {}
        self._db_available = False

    # ── DB Helpers ────────────────────────────────────────────────

    def _get_session_factory(self):
        from backend.db.engine import get_session_factory
        return get_session_factory()

    async def _db_repo_action(self, action, *args, **kwargs):
        """Run an action on the AgentRepository in a fresh session."""
        if not self._db_available:
            return None
        try:
            from backend.db.agent_repository import AgentRepository
            factory = self._get_session_factory()
            async with factory() as session:
                repo = AgentRepository(session)
                result = getattr(repo, action)(*args, **kwargs)
                if hasattr(result, "__await__"):
                    result = await result
                await session.commit()
                return result
        except Exception as e:
            logger.error(f"DB write failed ({action}): {e}")
            return None

    # ── Sync CRUD (in-memory cache only) ─────────────────────────

    def create(self, agent: AgentDefinition) -> AgentDefinition:
        agent.created_at = datetime.utcnow()
        agent.updated_at = datetime.utcnow()
        agent.endpoint.path_prefix = f"/agents/{agent.agent_id}"
        self._agents[agent.agent_id] = agent
        self._versions[agent.agent_id] = [copy.deepcopy(agent)]
        return agent

    def get(self, agent_id: str) -> Optional[AgentDefinition]:
        return self._agents.get(agent_id)

    def update(self, agent_id: str, updates: Dict[str, Any], change_note: str = "") -> Optional[AgentDefinition]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        for k, v in updates.items():
            if hasattr(agent, k) and k not in ("agent_id", "created_at"):
                setattr(agent, k, v)
        agent.version += 1
        agent.updated_at = datetime.utcnow()
        self._versions.setdefault(agent_id, []).append(copy.deepcopy(agent))
        return agent

    def delete(self, agent_id: str) -> bool:
        removed = self._agents.pop(agent_id, None)
        self._versions.pop(agent_id, None)
        return removed is not None

    def set_status(self, agent_id: str, status: AgentStatus) -> Optional[AgentDefinition]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.status = status
        agent.updated_at = datetime.utcnow()
        return agent

    def clone(self, agent_id: str, new_name: str) -> Optional[AgentDefinition]:
        original = self._agents.get(agent_id)
        if not original:
            return None
        cloned = copy.deepcopy(original)
        cloned.agent_id = f"agt-{uuid.uuid4().hex[:8]}"
        cloned.name = new_name
        cloned.version = 1
        cloned.status = AgentStatus.DRAFT
        cloned.metadata["cloned_from"] = agent_id
        return self.create(cloned)

    # ── Async CRUD (cache + DB write-through) ─────────────────────

    async def create_async(self, agent: AgentDefinition) -> AgentDefinition:
        self.create(agent)
        await self._db_repo_action("create", agent)
        return agent

    async def update_async(self, agent_id: str, updates: Dict[str, Any]) -> Optional[AgentDefinition]:
        agent = self.update(agent_id, updates)
        if agent:
            await self._db_repo_action("update", agent_id, updates)
        return agent

    async def delete_async(self, agent_id: str) -> bool:
        ok = self.delete(agent_id)
        if ok:
            await self._db_repo_action("delete", agent_id)
        return ok

    async def set_status_async(self, agent_id: str, status: AgentStatus) -> Optional[AgentDefinition]:
        agent = self.set_status(agent_id, status)
        if agent:
            await self._db_repo_action("update", agent_id, {"status": status})
        return agent

    async def clone_async(self, agent_id: str, new_name: str) -> Optional[AgentDefinition]:
        original = self._agents.get(agent_id)
        if not original:
            return None
        cloned = copy.deepcopy(original)
        cloned.agent_id = f"agt-{uuid.uuid4().hex[:8]}"
        cloned.name = new_name
        cloned.version = 1
        cloned.status = AgentStatus.DRAFT
        cloned.metadata["cloned_from"] = agent_id
        self.create(cloned)
        await self._db_repo_action("create", cloned)
        return cloned

    # ── Read Helpers ──────────────────────────────────────────────

    def list_all(self, status: Optional[AgentStatus] = None, owner_id: Optional[str] = None) -> List[AgentDefinition]:
        agents = list(self._agents.values())
        if status:
            agents = [a for a in agents if a.status == status]
        if owner_id:
            agents = [a for a in agents if a.access_control.owner_id == owner_id]
        return sorted(agents, key=lambda a: a.updated_at, reverse=True)

    def search(self, query: str) -> List[AgentDefinition]:
        q = query.lower()
        return [
            a for a in self._agents.values()
            if q in a.name.lower() or q in a.description.lower() or any(q in t for t in a.tags)
        ]

    def get_versions(self, agent_id: str) -> List[Dict[str, Any]]:
        return [
            {"version": a.version, "status": a.status.value, "updated_at": a.updated_at.isoformat()}
            for a in self._versions.get(agent_id, [])
        ]

    def get_version_detail(self, agent_id: str, version: int) -> Optional[Dict[str, Any]]:
        for a in self._versions.get(agent_id, []):
            if a.version == version:
                return a.model_dump(mode="json", by_alias=True)
        return None

    def rollback_to_version(self, agent_id: str, version: int, rolled_back_by: str = "system") -> Optional[AgentDefinition]:
        target = None
        for a in self._versions.get(agent_id, []):
            if a.version == version:
                target = a
                break
        if not target or agent_id not in self._agents:
            return None
        current = self._agents[agent_id]
        restored = copy.deepcopy(target)
        restored.version = current.version + 1
        restored.updated_at = datetime.utcnow()
        restored.metadata["rollback_from"] = version
        restored.metadata["rolled_back_by"] = rolled_back_by
        self._agents[agent_id] = restored
        self._versions.setdefault(agent_id, []).append(copy.deepcopy(restored))
        return restored

    async def rollback_to_version_async(self, agent_id: str, version: int, rolled_back_by: str = "system") -> Optional[AgentDefinition]:
        agent = self.rollback_to_version(agent_id, version, rolled_back_by)
        if agent:
            await self._db_repo_action("update", agent_id, {"version": agent.version})
        return agent

    def diff_versions(self, agent_id: str, version_a: int, version_b: int) -> Optional[Dict[str, Any]]:
        a_data = self.get_version_detail(agent_id, version_a)
        b_data = self.get_version_detail(agent_id, version_b)
        if not a_data or not b_data:
            return None
        changes = []
        skip = {"agent_id", "created_at", "updated_at", "version"}
        all_keys = set(a_data.keys()) | set(b_data.keys())
        for key in sorted(all_keys - skip):
            val_a = a_data.get(key)
            val_b = b_data.get(key)
            if val_a != val_b:
                changes.append({"field": key, f"v{version_a}": val_a, f"v{version_b}": val_b})
        return {
            "agent_id": agent_id,
            "version_a": version_a,
            "version_b": version_b,
            "changes": changes,
            "total_changes": len(changes),
        }

    def get_stats(self) -> Dict[str, Any]:
        agents = list(self._agents.values())
        by_status: Dict[str, int] = {}
        for a in agents:
            by_status[a.status.value] = by_status.get(a.status.value, 0) + 1
        return {
            "total_agents": len(agents),
            "by_status": by_status,
            "with_rag": sum(1 for a in agents if a.rag_config.enabled),
            "with_tools": sum(1 for a in agents if a.tools),
            "with_db": sum(1 for a in agents if a.db_config.structured_enabled or a.db_config.unstructured_enabled),
        }
