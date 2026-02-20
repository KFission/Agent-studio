"""
JAI Agent OS — V2 API Routes
Auth, Users, Agent-as-a-Service, Orchestrator, Tool Builder, RAG, Memory, DB
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent_service.agent_registry import (
    AgentDefinition, AgentStatus, ModelConfig, RAGConfig,
    MemoryConfig, DBConfig, AccessControl,
)
from backend.agent_service.agent_db import DBConnection, DBType
from backend.orchestrator.orchestrator import (
    Pipeline, PipelineStep, OrchestrationPattern,
)
from backend.tool_builder.tool_registry import (
    ToolDefinition, ToolType, CodeToolConfig, CodeLanguage, RestApiToolConfig,
    McpToolConfig, KeyValuePair, HttpMethod, AuthType, BodyType,
)
from backend.db.engine import get_db_session
from backend.db.agent_repository import AgentRepository

router = APIRouter()


# ── Request Models ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""
    roles: List[str] = Field(default_factory=lambda: ["viewer"])

class CreateAgentRequest(BaseModel):
    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    model_config_: dict = Field(default_factory=dict, alias="model_config")
    context: str = ""
    rag_enabled: bool = False
    memory_enabled: bool = True
    owner_id: str = ""

class AddMessageRequest(BaseModel):
    role: str = "user"
    content: str
    session_id: str = "default"

class StoreLongTermRequest(BaseModel):
    content: str
    metadata: dict = Field(default_factory=dict)

class CreateCollectionRequest(BaseModel):
    name: str
    description: str = ""
    agent_id: Optional[str] = None

class AddDocumentRequest(BaseModel):
    content: str
    metadata: dict = Field(default_factory=dict)

class RetrieveRequest(BaseModel):
    query: str
    collection_ids: List[str] = Field(default_factory=list)
    top_k: int = 5

class RegisterDBRequest(BaseModel):
    name: str
    db_type: str = "postgres"
    host: str = ""
    port: int = 5432
    database: str = ""
    schema_name: str = "public"
    username: str = ""

class ExecuteQueryRequest(BaseModel):
    query: str
    parameters: dict = Field(default_factory=dict)
    read_only: bool = True

class CreatePipelineRequest(BaseModel):
    name: str
    description: str = ""
    pattern: str = "sequential"
    steps: List[dict] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

class ExecutePipelineRequest(BaseModel):
    input_data: dict = Field(default_factory=dict)

class CreateToolRequest(BaseModel):
    name: str
    description: str = ""
    tool_type: str = "rest_api"  # code, rest_api, mcp
    tags: List[str] = Field(default_factory=list)
    # Type-specific config — only one should be provided
    code_config: Optional[dict] = None
    rest_api_config: Optional[dict] = None
    mcp_config: Optional[dict] = None

class ExecuteToolRequest(BaseModel):
    inputs: dict = Field(default_factory=dict)
    agent_id: Optional[str] = None

class ImportAgentRequest(BaseModel):
    agent_data: Dict[str, Any]
    new_name: Optional[str] = None
    import_as_draft: bool = True

class BulkExportRequest(BaseModel):
    agent_ids: List[str]

class AssignRoleRequest(BaseModel):
    user_id: str
    role_name: str


def register_v2_routes(
    app_router,
    keycloak, rbac_manager, user_manager,
    agent_registry, agent_memory, agent_rag, agent_db,
    orchestrator_inst, tool_registry_inst,
):
    """Register all V2 routes. Called from server.py with global instances."""

    # ══════════════════════════════════════════════════════════════
    # AUTH & USERS
    # ══════════════════════════════════════════════════════════════

    # ── Rate limiter for auth endpoints (5 attempts / 60s per IP) ──
    from collections import defaultdict
    import time as _rl_time
    _login_attempts: Dict[str, list] = defaultdict(list)
    _LOGIN_RATE_LIMIT = 5
    _LOGIN_RATE_WINDOW = 60  # seconds

    def _check_rate_limit(client_ip: str) -> bool:
        """Return True if request is allowed, False if rate-limited."""
        now = _rl_time.time()
        # Prune expired entries
        _login_attempts[client_ip] = [
            ts for ts in _login_attempts[client_ip] if now - ts < _LOGIN_RATE_WINDOW
        ]
        if len(_login_attempts[client_ip]) >= _LOGIN_RATE_LIMIT:
            return False
        _login_attempts[client_ip].append(now)
        return True

    @app_router.post("/auth/login")
    async def login(req: LoginRequest, request: Request):
        """Authenticate user against DB with password hash verification."""
        import secrets, logging
        _log = logging.getLogger("auth")

        # Rate limit check
        client_ip = request.client.host if request.client else "unknown"
        if not _check_rate_limit(client_ip):
            _log.warning(f"Rate limited login attempt from {client_ip}")
            raise HTTPException(
                429,
                f"Too many login attempts. Try again in {_LOGIN_RATE_WINDOW} seconds.",
            )

        try:
            from sqlalchemy import select
            from backend.db.engine import get_session_factory
            from backend.db.models import UserModel
            from backend.db.seed_db import verify_password

            factory = get_session_factory()
            async with factory() as session:
                stmt = select(UserModel).where(
                    (UserModel.username == req.username) | (UserModel.email == req.username)
                )
                user = (await session.execute(stmt)).scalar_one_or_none()
                if not user or not verify_password(req.password, user.password_hash):
                    raise HTTPException(401, "Invalid username or password")
                if not user.is_active:
                    raise HTTPException(403, "Account is disabled")

                token = f"jai-{secrets.token_urlsafe(32)}"
                roles = user.roles or ["viewer"]
                # Store the actual token in cache for auth middleware validation
                from backend.auth.keycloak_provider import TokenInfo
                import time as _t
                keycloak._token_cache[token] = TokenInfo(
                    sub=user.id,
                    email=user.email,
                    name=user.display_name or user.username,
                    preferred_username=user.username,
                    realm_access={"roles": roles},
                    exp=int(_t.time()) + 86400,
                )

                return {
                    "access_token": token,
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "display_name": user.display_name,
                    "roles": roles,
                    "expires_in": 86400,
                }
        except HTTPException:
            raise
        except Exception as exc:
            _log.error(f"Login error: {exc}", exc_info=True)
            raise HTTPException(401, "Invalid username or password")

    @app_router.get("/auth/me")
    async def auth_me(token: str = Query(...)):
        info = keycloak._token_cache.get(token)
        if not info:
            raise HTTPException(401, "Invalid token")
        return {"user_id": info.sub, "email": info.email, "name": info.name, "roles": info.realm_access.get("roles", [])}

    @app_router.get("/users")
    async def list_users(tenant_id: Optional[str] = None):
        users = user_manager.list_users(tenant_id)
        return {"count": len(users), "users": [u.model_dump(mode="json", exclude={"api_keys"}) for u in users]}

    @app_router.post("/users")
    async def create_user(req: CreateUserRequest):
        """Create a new user in DB (with password hash) and in-memory manager."""
        import uuid as _uuid
        from sqlalchemy import select
        from backend.db.engine import get_session_factory
        from backend.db.models import UserModel
        from backend.db.seed_db import _hash_password
        from backend.auth.user_manager import UserProfile

        if not req.password or len(req.password) < 6:
            raise HTTPException(400, "Password must be at least 6 characters")

        factory = get_session_factory()
        async with factory() as session:
            # Check for duplicate email/username
            existing = (await session.execute(
                select(UserModel).where(
                    (UserModel.email == req.email) | (UserModel.username == req.username)
                )
            )).scalar_one_or_none()
            if existing:
                raise HTTPException(400, "A user with this email or username already exists")

            user_id = f"user-{_uuid.uuid4().hex[:8]}"
            display_name = f"{req.first_name} {req.last_name}".strip() or req.username
            db_user = UserModel(
                id=user_id,
                username=req.username,
                email=req.email,
                password_hash=_hash_password(req.password),
                first_name=req.first_name,
                last_name=req.last_name,
                display_name=display_name,
                tenant_id="default",
                roles=req.roles,
                is_active=True,
            )
            session.add(db_user)
            await session.commit()

        # Also add to in-memory manager so user appears in list immediately
        profile = UserProfile(
            user_id=user_id, username=req.username, email=req.email,
            first_name=req.first_name, last_name=req.last_name,
            display_name=display_name, tenant_id="default", roles=req.roles,
        )
        user_manager._users[user_id] = profile
        user_manager._email_index[req.email] = user_id
        user_manager._username_index[req.username] = user_id
        for role in req.roles:
            rbac_manager.assign_role(user_id, role)

        return {"status": "created", "user_id": user_id}

    @app_router.get("/users/{user_id}")
    async def get_user(user_id: str):
        user = user_manager.get_user(user_id)
        if not user:
            raise HTTPException(404, "User not found")
        return user.model_dump(mode="json", exclude={"api_keys"})

    @app_router.delete("/users/{user_id}")
    async def delete_user(user_id: str):
        if not user_manager.delete_user(user_id):
            raise HTTPException(404, "User not found")
        return {"status": "deleted"}

    @app_router.get("/users/{user_id}/roles")
    async def get_user_roles(user_id: str):
        return {"user_id": user_id, "roles": rbac_manager.get_user_roles(user_id)}

    @app_router.post("/users/{user_id}/api-key")
    async def generate_api_key(user_id: str, name: str = Query(default="default")):
        result = user_manager.generate_api_key(user_id, name)
        if not result:
            raise HTTPException(404, "User not found")
        return result

    @app_router.get("/users/stats/summary")
    async def user_stats():
        return user_manager.get_stats()

    # ── Roles & RBAC ──────────────────────────────────────────────

    @app_router.get("/roles")
    async def list_roles():
        roles = rbac_manager.list_roles()
        return {"count": len(roles), "roles": [{"name": r.name, "description": r.description, "permissions": len(r.permissions), "is_system": r.is_system} for r in roles]}

    @app_router.post("/roles/assign")
    async def assign_role(req: AssignRoleRequest):
        if not rbac_manager.assign_role(req.user_id, req.role_name):
            raise HTTPException(400, f"Role '{req.role_name}' not found")
        return {"status": "assigned"}

    @app_router.post("/roles/revoke")
    async def revoke_role(req: AssignRoleRequest):
        rbac_manager.revoke_role(req.user_id, req.role_name)
        return {"status": "revoked"}

    @app_router.get("/audit-log")
    async def audit_log(limit: int = Query(default=50)):
        return {"entries": rbac_manager.get_audit_log(limit)}

    # ══════════════════════════════════════════════════════════════
    # AGENT-AS-A-SERVICE
    # ══════════════════════════════════════════════════════════════

    @app_router.get("/agents")
    async def list_agents(status: Optional[str] = None, owner_id: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
        # Get agents from in-memory registry
        s = AgentStatus(status) if status else None
        memory_agents = agent_registry.list_all(s, owner_id)
        
        # Also load agents from PostgreSQL database
        db_agents = []
        try:
            repo = AgentRepository(db)
            db_agents = await repo.list_all(s, owner_id, limit=500, offset=0)
        except Exception as e:
            print(f"[Agent Persistence] Failed to load from DB: {e}")
        
        # Merge and deduplicate by agent_id (prefer in-memory version if exists in both)
        agent_map = {}
        for a in db_agents:
            agent_map[a.agent_id] = {
                "agent_id": a.agent_id, "name": a.name, "description": a.description, 
                "status": a.status.value, "version": a.version, "tags": a.tags,
                "model": a.model_config_.model_id if hasattr(a, 'model_config_') else "",
                "rag_enabled": a.rag_config.enabled, "tools_count": len(a.tools), 
                "updated_at": a.updated_at.isoformat()
            }
        for a in memory_agents:
            agent_map[a.agent_id] = {
                "agent_id": a.agent_id, "name": a.name, "description": a.description, 
                "status": a.status.value, "version": a.version, "tags": a.tags,
                "model": a.model_config_.model_id if hasattr(a, 'model_config_') else "",
                "rag_enabled": a.rag_config.enabled, "tools_count": len(a.tools), 
                "updated_at": a.updated_at.isoformat()
            }
        
        agents_list = list(agent_map.values())
        return {"count": len(agents_list), "agents": agents_list}

    @app_router.post("/agents")
    async def create_agent(req: CreateAgentRequest, db: AsyncSession = Depends(get_db_session)):
        mc = ModelConfig(**req.model_config_) if req.model_config_ else ModelConfig()
        agent = AgentDefinition(
            name=req.name, description=req.description, tags=req.tags,
            rag_config=RAGConfig(enabled=req.rag_enabled),
            memory_config=MemoryConfig(short_term_enabled=req.memory_enabled, long_term_enabled=req.memory_enabled),
            context=req.context,
            access_control=AccessControl(owner_id=req.owner_id),
        )
        agent.model_config_ = mc
        # Save to in-memory registry
        created = await agent_registry.create_async(agent)
        # Also persist to PostgreSQL database
        try:
            repo = AgentRepository(db)
            await repo.create(created, credential_id=None)
        except Exception as e:
            print(f"[Agent Persistence] Failed to save to DB: {e}")
        return {"status": "created", "agent_id": created.agent_id}

    @app_router.put("/agents/{agent_id}")
    async def update_agent(agent_id: str, req: dict, db: AsyncSession = Depends(get_db_session)):
        updates = {}
        if "name" in req: updates["name"] = req["name"]
        if "description" in req: updates["description"] = req["description"]
        if "tags" in req: updates["tags"] = req["tags"]
        if "context" in req: updates["context"] = req["context"]
        if "status" in req: updates["status"] = AgentStatus(req["status"])
        if "model_config" in req or "model_config_" in req:
            mc_data = req.get("model_config") or req.get("model_config_", {})
            updates["model_config_"] = ModelConfig(**mc_data)
        if "rag_enabled" in req: updates["rag_config"] = RAGConfig(enabled=req["rag_enabled"])
        if "tools" in req:
            updates["tools"] = [ToolBinding(**t) if isinstance(t, dict) else t for t in req["tools"]]
        # Update in-memory registry
        agent = await agent_registry.update_async(agent_id, updates)
        if not agent:
            raise HTTPException(404, "Agent not found")
        # Also update in PostgreSQL database
        try:
            repo = AgentRepository(db)
            await repo.update(agent_id, updates)
        except Exception as e:
            print(f"[Agent Persistence] Failed to update DB: {e}")
        return {"status": "updated", "agent_id": agent.agent_id, "version": agent.version}

    @app_router.get("/agents/stats")
    async def agent_stats():
        return agent_registry.get_stats()

    @app_router.get("/agents/{agent_id}")
    async def get_agent(agent_id: str):
        agent = agent_registry.get(agent_id)
        if not agent:
            raise HTTPException(404, "Agent not found")
        return agent.model_dump(mode="json", by_alias=True)

    @app_router.delete("/agents/{agent_id}")
    async def delete_agent(agent_id: str):
        if not await agent_registry.delete_async(agent_id):
            raise HTTPException(404, "Agent not found")
        return {"status": "deleted"}

    @app_router.post("/agents/{agent_id}/status/{status}")
    async def set_agent_status(agent_id: str, status: str):
        result = await agent_registry.set_status_async(agent_id, AgentStatus(status))
        if not result:
            raise HTTPException(404, "Agent not found")
        return {"status": status}

    @app_router.post("/agents/{agent_id}/clone")
    async def clone_agent(agent_id: str, name: str = Query(...)):
        result = await agent_registry.clone_async(agent_id, name)
        if not result:
            raise HTTPException(404, "Agent not found")
        return {"status": "cloned", "agent_id": result.agent_id}

    @app_router.get("/agents/{agent_id}/versions")
    async def agent_versions(agent_id: str):
        return {"versions": agent_registry.get_versions(agent_id)}

    @app_router.get("/agents/{agent_id}/versions/{version}")
    async def get_agent_version(agent_id: str, version: int):
        detail = agent_registry.get_version_detail(agent_id, version)
        if not detail:
            raise HTTPException(404, f"Version {version} not found for agent {agent_id}")
        return detail

    @app_router.post("/agents/{agent_id}/rollback/{version}")
    async def rollback_agent(agent_id: str, version: int,
                             rolled_back_by: str = Query(default="admin")):
        agent = await agent_registry.rollback_to_version_async(agent_id, version, rolled_back_by)
        if not agent:
            raise HTTPException(404, f"Cannot rollback: agent or version {version} not found")
        return {
            "status": "rolled_back",
            "agent_id": agent_id,
            "restored_from_version": version,
            "new_version": agent.version,
        }

    @app_router.get("/agents/{agent_id}/diff/{version_a}/{version_b}")
    async def diff_agent_versions(agent_id: str, version_a: int, version_b: int):
        diff = agent_registry.diff_versions(agent_id, version_a, version_b)
        if not diff:
            raise HTTPException(404, f"Cannot diff: agent or versions not found")
        return diff

    # ── Agent Import / Export ─────────────────────────────────────

    @app_router.get("/agents/{agent_id}/export")
    async def export_agent(agent_id: str):
        """Export a single agent as a portable JSON document."""
        agent = agent_registry.get(agent_id)
        if not agent:
            raise HTTPException(404, "Agent not found")
        data = agent.model_dump(mode="json", by_alias=True)
        # Strip server-internal fields that shouldn't be imported verbatim
        export_doc = {
            "_export_format": "jai-agent-os",
            "_export_version": 1,
            "agent": {
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "version": data.get("version", 1),
                "status": data.get("status", "draft"),
                "tags": data.get("tags", []),
                "model_config": data.get("model_config", {}),
                "context": data.get("context", ""),
                "prompt_template_id": data.get("prompt_template_id"),
                "rag_config": data.get("rag_config", {}),
                "memory_config": data.get("memory_config", {}),
                "db_config": data.get("db_config", {}),
                "tools": data.get("tools", []),
                "endpoint": data.get("endpoint", {}),
                "access_control": data.get("access_control", {}),
                "graph_manifest_id": data.get("graph_manifest_id"),
                "metadata": data.get("metadata", {}),
            },
        }
        return export_doc

    @app_router.post("/agents/export-bulk")
    async def export_agents_bulk(req: BulkExportRequest):
        """Export multiple agents as a single JSON document."""
        results = []
        for aid in req.agent_ids:
            agent = agent_registry.get(aid)
            if not agent:
                continue
            data = agent.model_dump(mode="json", by_alias=True)
            results.append({
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "version": data.get("version", 1),
                "status": data.get("status", "draft"),
                "tags": data.get("tags", []),
                "model_config": data.get("model_config", {}),
                "context": data.get("context", ""),
                "prompt_template_id": data.get("prompt_template_id"),
                "rag_config": data.get("rag_config", {}),
                "memory_config": data.get("memory_config", {}),
                "db_config": data.get("db_config", {}),
                "tools": data.get("tools", []),
                "endpoint": data.get("endpoint", {}),
                "access_control": data.get("access_control", {}),
                "graph_manifest_id": data.get("graph_manifest_id"),
                "metadata": data.get("metadata", {}),
            })
        return {
            "_export_format": "jai-agent-os",
            "_export_version": 1,
            "agents": results,
            "count": len(results),
        }

    @app_router.post("/agents/import")
    async def import_agent(req: ImportAgentRequest):
        """Import an agent from a JSON export document. Creates a new agent."""
        import uuid as _uuid
        agent_data = req.agent_data

        # Support both single-agent export format and raw agent dict
        if "agent" in agent_data and isinstance(agent_data["agent"], dict):
            agent_data = agent_data["agent"]

        name = req.new_name or agent_data.get("name", "Imported Agent")
        mc_data = agent_data.get("model_config") or agent_data.get("model_config_") or {}
        rag_data = agent_data.get("rag_config") or {}
        mem_data = agent_data.get("memory_config") or {}
        db_data = agent_data.get("db_config") or {}
        ac_data = agent_data.get("access_control") or {}

        from backend.agent_service.agent_registry import ToolBinding
        tools = []
        for t in agent_data.get("tools", []):
            if isinstance(t, dict):
                tools.append(ToolBinding(**{k: v for k, v in t.items() if k in ToolBinding.model_fields}))

        new_id = f"agt-{_uuid.uuid4().hex[:8]}"
        agent = AgentDefinition(
            agent_id=new_id,
            name=name,
            description=agent_data.get("description", ""),
            tags=agent_data.get("tags", []) + ["imported"],
            context=agent_data.get("context", ""),
            prompt_template_id=agent_data.get("prompt_template_id"),
            graph_manifest_id=agent_data.get("graph_manifest_id"),
            status=AgentStatus.DRAFT if req.import_as_draft else AgentStatus(agent_data.get("status", "draft")),
            access_control=AccessControl(**{k: v for k, v in ac_data.items() if k in AccessControl.model_fields}),
            metadata={
                **agent_data.get("metadata", {}),
                "imported_from": agent_data.get("name", "unknown"),
                "imported_at": __import__("datetime").datetime.utcnow().isoformat(),
            },
        )
        if mc_data:
            agent.model_config_ = ModelConfig(**{k: v for k, v in mc_data.items() if k in ModelConfig.model_fields})
        if rag_data:
            agent.rag_config = RAGConfig(**{k: v for k, v in rag_data.items() if k in RAGConfig.model_fields})
        if mem_data:
            agent.memory_config = MemoryConfig(**{k: v for k, v in mem_data.items() if k in MemoryConfig.model_fields})
        if db_data:
            agent.db_config = DBConfig(**{k: v for k, v in db_data.items() if k in DBConfig.model_fields})
        agent.tools = tools

        created = await agent_registry.create_async(agent)
        return {
            "status": "imported",
            "agent_id": created.agent_id,
            "name": created.name,
            "version": created.version,
        }

    @app_router.post("/agents/import-bulk")
    async def import_agents_bulk(req: dict):
        """Import multiple agents from a bulk export JSON document."""
        import uuid as _uuid
        from backend.agent_service.agent_registry import ToolBinding

        agents_data = req.get("agents", [])
        # Also support the single-agent format wrapped in a list
        if not agents_data and "agent" in req:
            agents_data = [req["agent"]]

        imported = []
        errors = []
        for i, agent_data in enumerate(agents_data):
            try:
                name = agent_data.get("name", f"Imported Agent {i+1}")
                mc_data = agent_data.get("model_config") or agent_data.get("model_config_") or {}
                rag_data = agent_data.get("rag_config") or {}
                mem_data = agent_data.get("memory_config") or {}
                db_data = agent_data.get("db_config") or {}
                ac_data = agent_data.get("access_control") or {}

                tools = []
                for t in agent_data.get("tools", []):
                    if isinstance(t, dict):
                        tools.append(ToolBinding(**{k: v for k, v in t.items() if k in ToolBinding.model_fields}))

                new_id = f"agt-{_uuid.uuid4().hex[:8]}"
                agent = AgentDefinition(
                    agent_id=new_id, name=name,
                    description=agent_data.get("description", ""),
                    tags=agent_data.get("tags", []) + ["imported"],
                    context=agent_data.get("context", ""),
                    prompt_template_id=agent_data.get("prompt_template_id"),
                    graph_manifest_id=agent_data.get("graph_manifest_id"),
                    status=AgentStatus.DRAFT,
                    access_control=AccessControl(**{k: v for k, v in ac_data.items() if k in AccessControl.model_fields}),
                    metadata={**agent_data.get("metadata", {}), "imported_from": name, "imported_at": __import__("datetime").datetime.utcnow().isoformat()},
                )
                if mc_data:
                    agent.model_config_ = ModelConfig(**{k: v for k, v in mc_data.items() if k in ModelConfig.model_fields})
                if rag_data:
                    agent.rag_config = RAGConfig(**{k: v for k, v in rag_data.items() if k in RAGConfig.model_fields})
                if mem_data:
                    agent.memory_config = MemoryConfig(**{k: v for k, v in mem_data.items() if k in MemoryConfig.model_fields})
                if db_data:
                    agent.db_config = DBConfig(**{k: v for k, v in db_data.items() if k in DBConfig.model_fields})
                agent.tools = tools

                created = await agent_registry.create_async(agent)
                imported.append({"agent_id": created.agent_id, "name": created.name})
            except Exception as e:
                errors.append({"index": i, "name": agent_data.get("name", "?"), "error": str(e)})

        return {
            "status": "bulk_import_complete",
            "imported_count": len(imported),
            "error_count": len(errors),
            "imported": imported,
            "errors": errors,
        }

    # ── Agent Memory ──────────────────────────────────────────────

    @app_router.post("/agents/{agent_id}/memory/message")
    async def add_memory_message(agent_id: str, req: AddMessageRequest):
        entry = agent_memory.add_message(agent_id, req.session_id, req.role, req.content)
        return {"entry_id": entry.entry_id}

    @app_router.get("/agents/{agent_id}/memory/conversation")
    async def get_conversation(agent_id: str, session_id: str = "default", limit: int = 50):
        entries = agent_memory.get_conversation(agent_id, session_id, limit)
        return {"count": len(entries), "messages": [e.model_dump(mode="json") for e in entries]}

    @app_router.get("/agents/{agent_id}/memory/sessions")
    async def list_sessions(agent_id: str):
        return {"sessions": agent_memory.list_sessions(agent_id)}

    @app_router.post("/agents/{agent_id}/memory/long-term")
    async def store_long_term(agent_id: str, req: StoreLongTermRequest):
        entry = agent_memory.store_long_term(agent_id, req.content, req.metadata)
        return {"entry_id": entry.entry_id}

    @app_router.get("/agents/{agent_id}/memory/long-term")
    async def get_long_term(agent_id: str, limit: int = 20):
        entries = agent_memory.get_long_term(agent_id, limit)
        return {"count": len(entries), "entries": [e.model_dump(mode="json") for e in entries]}

    @app_router.get("/agents/{agent_id}/memory/stats")
    async def memory_stats(agent_id: str):
        return agent_memory.get_agent_memory_stats(agent_id)

    @app_router.delete("/agents/{agent_id}/memory")
    async def clear_memory(agent_id: str):
        return agent_memory.clear_all(agent_id)

    # ══════════════════════════════════════════════════════════════
    # RAG COLLECTIONS & DOCUMENTS
    # ══════════════════════════════════════════════════════════════

    @app_router.get("/rag/collections")
    async def list_collections(agent_id: Optional[str] = None):
        cols = agent_rag.list_collections(agent_id)
        return {"count": len(cols), "collections": [c.model_dump(mode="json") for c in cols]}

    @app_router.post("/rag/collections")
    async def create_collection(req: CreateCollectionRequest):
        col = agent_rag.create_collection(req.name, req.agent_id, req.description)
        return {"status": "created", "collection_id": col.collection_id}

    @app_router.delete("/rag/collections/{collection_id}")
    async def delete_collection(collection_id: str):
        if not agent_rag.delete_collection(collection_id):
            raise HTTPException(404, "Collection not found")
        return {"status": "deleted"}

    @app_router.post("/rag/collections/{collection_id}/documents")
    async def add_document(collection_id: str, req: AddDocumentRequest):
        doc = agent_rag.add_document(collection_id, req.content, req.metadata)
        if not doc:
            raise HTTPException(404, "Collection not found")
        return {"status": "added", "doc_id": doc.doc_id}

    @app_router.get("/rag/collections/{collection_id}/documents")
    async def list_documents(collection_id: str, limit: int = 50):
        docs = agent_rag.get_documents(collection_id, limit)
        return {"count": len(docs), "documents": [d.model_dump(mode="json") for d in docs]}

    @app_router.post("/rag/retrieve")
    async def retrieve(req: RetrieveRequest):
        results = agent_rag.retrieve(req.collection_ids, req.query, req.top_k)
        return {"count": len(results), "results": [r.model_dump() for r in results]}

    @app_router.get("/rag/stats")
    async def rag_stats():
        return agent_rag.get_stats()

    # ══════════════════════════════════════════════════════════════
    # DATABASE CONNECTIONS
    # ══════════════════════════════════════════════════════════════

    @app_router.get("/db/connections")
    async def list_db_connections(db_type: Optional[str] = None):
        t = DBType(db_type) if db_type else None
        conns = agent_db.list_connections(t)
        return {"count": len(conns), "connections": [c.model_dump(mode="json", exclude={"password_secret_ref"}) for c in conns]}

    @app_router.post("/db/connections")
    async def register_db(req: RegisterDBRequest):
        conn = DBConnection(name=req.name, db_type=DBType(req.db_type), host=req.host, port=req.port, database=req.database, schema_name=req.schema_name, username=req.username)
        agent_db.register_connection(conn)
        return {"status": "registered", "connection_id": conn.connection_id}

    @app_router.delete("/db/connections/{connection_id}")
    async def delete_db(connection_id: str):
        if not agent_db.delete_connection(connection_id):
            raise HTTPException(404, "Connection not found")
        return {"status": "deleted"}

    @app_router.post("/db/connections/{connection_id}/test")
    async def test_db(connection_id: str):
        return agent_db.test_connection(connection_id)

    @app_router.post("/db/connections/{connection_id}/query")
    async def execute_db_query(connection_id: str, req: ExecuteQueryRequest, agent_id: Optional[str] = None):
        result = agent_db.execute_query(connection_id, req.query, req.parameters, agent_id, req.read_only)
        if not result.success:
            raise HTTPException(400, result.error)
        return result.model_dump()

    @app_router.get("/db/connections/{connection_id}/tables")
    async def list_tables(connection_id: str):
        return {"tables": agent_db.get_tables(connection_id)}

    @app_router.post("/db/bind/{agent_id}/{connection_id}")
    async def bind_db(agent_id: str, connection_id: str):
        if not agent_db.bind_to_agent(agent_id, connection_id):
            raise HTTPException(400, "Connection not found")
        return {"status": "bound"}

    @app_router.get("/db/stats")
    async def db_stats():
        return agent_db.get_stats()

    # ══════════════════════════════════════════════════════════════
    # ORCHESTRATOR
    # ══════════════════════════════════════════════════════════════

    @app_router.get("/orchestrator/pipelines")
    async def list_pipelines(status: Optional[str] = None):
        pipes = orchestrator_inst.list_pipelines(status)
        return {"count": len(pipes), "pipelines": [
            {"pipeline_id": p.pipeline_id, "name": p.name, "pattern": p.pattern.value,
             "steps": len(p.steps), "status": p.status, "version": p.version, "updated_at": p.updated_at.isoformat()}
            for p in pipes
        ]}

    @app_router.post("/orchestrator/pipelines")
    async def create_pipeline(req: CreatePipelineRequest):
        steps = [PipelineStep(**s) for s in req.steps]
        pipe = Pipeline(name=req.name, description=req.description, pattern=OrchestrationPattern(req.pattern), steps=steps, tags=req.tags)
        created = orchestrator_inst.create_pipeline(pipe)
        return {"status": "created", "pipeline_id": created.pipeline_id}

    @app_router.get("/orchestrator/pipelines/{pipeline_id}")
    async def get_pipeline(pipeline_id: str):
        pipe = orchestrator_inst.get_pipeline(pipeline_id)
        if not pipe:
            raise HTTPException(404, "Pipeline not found")
        return pipe.model_dump(mode="json")

    @app_router.delete("/orchestrator/pipelines/{pipeline_id}")
    async def delete_pipeline(pipeline_id: str):
        if not orchestrator_inst.delete_pipeline(pipeline_id):
            raise HTTPException(404, "Pipeline not found")
        return {"status": "deleted"}

    @app_router.post("/orchestrator/pipelines/{pipeline_id}/execute")
    async def execute_pipeline(pipeline_id: str, req: ExecutePipelineRequest):
        run = orchestrator_inst.execute_pipeline(pipeline_id, req.input_data)
        return run.model_dump(mode="json")

    @app_router.get("/orchestrator/runs")
    async def list_pipeline_runs(pipeline_id: Optional[str] = None, limit: int = 20):
        runs = orchestrator_inst.list_runs(pipeline_id, limit)
        return {"count": len(runs), "runs": [
            {"run_id": r.run_id, "pipeline_id": r.pipeline_id, "pipeline_name": r.pipeline_name,
             "status": r.status, "steps_completed": r.steps_completed, "total_latency_ms": r.total_latency_ms}
            for r in runs
        ]}

    @app_router.get("/orchestrator/stats")
    async def orchestrator_stats():
        return orchestrator_inst.get_stats()

    # ══════════════════════════════════════════════════════════════
    # TOOL BUILDER
    # ══════════════════════════════════════════════════════════════

    @app_router.get("/tools")
    async def list_tools(tool_type: Optional[str] = None, status: Optional[str] = None):
        tt = ToolType(tool_type) if tool_type else None
        tools = tool_registry_inst.list_all(tt, status)
        return {"count": len(tools), "tools": [
            {"tool_id": t.tool_id, "name": t.name, "description": t.description, "tool_type": t.tool_type.value,
             "status": t.status, "version": t.version, "tags": t.tags,
             "executions": t.execution_count, "avg_latency_ms": t.avg_latency_ms, "success_rate": t.success_rate,
             "last_execution": t.last_execution.isoformat() if t.last_execution else None,
             "updated_at": t.updated_at.isoformat()}
            for t in tools
        ]}

    @app_router.post("/tools")
    async def create_tool(req: CreateToolRequest):
        tool = ToolDefinition(name=req.name, description=req.description, tool_type=ToolType(req.tool_type), tags=req.tags)
        if req.tool_type == "code" and req.code_config:
            tool.code_config = CodeToolConfig(**req.code_config)
        elif req.tool_type == "rest_api" and req.rest_api_config:
            tool.rest_api_config = RestApiToolConfig(**req.rest_api_config)
        elif req.tool_type == "mcp" and req.mcp_config:
            tool.mcp_config = McpToolConfig(**req.mcp_config)
        created = tool_registry_inst.create(tool)
        return {"status": "created", "tool_id": created.tool_id}

    @app_router.put("/tools/{tool_id}")
    async def update_tool(tool_id: str, req: CreateToolRequest):
        updates: Dict[str, Any] = {"name": req.name, "description": req.description, "tags": req.tags}
        if req.tool_type == "code" and req.code_config:
            updates["code_config"] = CodeToolConfig(**req.code_config)
        elif req.tool_type == "rest_api" and req.rest_api_config:
            updates["rest_api_config"] = RestApiToolConfig(**req.rest_api_config)
        elif req.tool_type == "mcp" and req.mcp_config:
            updates["mcp_config"] = McpToolConfig(**req.mcp_config)
        result = tool_registry_inst.update(tool_id, updates)
        if not result:
            raise HTTPException(404, "Tool not found")
        return {"status": "updated", "tool_id": tool_id, "version": result.version}

    @app_router.get("/tools/{tool_id}")
    async def get_tool(tool_id: str):
        tool = tool_registry_inst.get(tool_id)
        if not tool:
            raise HTTPException(404, "Tool not found")
        return tool.model_dump(mode="json")

    @app_router.delete("/tools/{tool_id}")
    async def delete_tool(tool_id: str):
        if not tool_registry_inst.delete(tool_id):
            raise HTTPException(404, "Tool not found")
        return {"status": "deleted"}

    @app_router.post("/tools/{tool_id}/execute")
    async def execute_tool(tool_id: str, req: ExecuteToolRequest):
        result = tool_registry_inst.execute(tool_id, req.inputs, req.agent_id)
        return result.model_dump()

    @app_router.post("/tools/{tool_id}/clone")
    async def clone_tool(tool_id: str, name: str = Query(...)):
        result = tool_registry_inst.clone(tool_id, name)
        if not result:
            raise HTTPException(404, "Tool not found")
        return {"status": "cloned", "tool_id": result.tool_id}

    @app_router.get("/tools/search/{query}")
    async def search_tools(query: str):
        results = tool_registry_inst.search(query)
        return {"count": len(results), "results": [{"tool_id": t.tool_id, "name": t.name, "tool_type": t.tool_type.value} for t in results]}

    @app_router.get("/tools/stats/summary")
    async def tool_stats():
        return tool_registry_inst.get_stats()

    class McpDiscoverRequest(BaseModel):
        server_url: str
        headers: Dict[str, str] = Field(default_factory=dict)

    @app_router.post("/tools/mcp/discover")
    async def mcp_discover(req: McpDiscoverRequest):
        """Discover available tools on an MCP server."""
        result = tool_registry_inst.discover_mcp(req.server_url, req.headers or None)
        if not result.success:
            raise HTTPException(400, result.error)
        return {"tools": result.output}

    @app_router.get("/tools/{tool_id}/logs")
    async def tool_execution_logs(tool_id: str, limit: int = Query(default=50, le=200)):
        """Get execution history for a specific tool."""
        return {"logs": tool_registry_inst.get_execution_log(tool_id, limit)}
