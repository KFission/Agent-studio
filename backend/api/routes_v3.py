"""
JAI Agent OS — V3 API Routes
Multi-tenancy, Agent-as-a-Service Gateway, LLM Logs, Threads, Inbox, Settings API Keys
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Header, Request
from pydantic import BaseModel, Field


router = APIRouter()


# ── Request Models ────────────────────────────────────────────────

class CreateTenantRequest(BaseModel):
    name: str
    owner_email: str
    tier: str = "free"
    domain: str = ""
    settings: Dict = Field(default_factory=dict)

class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    tier: Optional[str] = None
    is_active: Optional[bool] = None
    domain: Optional[str] = None
    settings: Optional[Dict] = None

class ChatCompletionRequest(BaseModel):
    model: str = "gemini-2.5-flash"
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    stream: bool = False
    agent_id: Optional[str] = None
    tools: Optional[List[Dict]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CreateThreadRequest(BaseModel):
    agent_id: str
    tenant_id: str = "tenant-default"
    user_id: str = ""
    title: str = ""
    config: Dict = Field(default_factory=dict)

class AddMessageRequest(BaseModel):
    role: str = "user"
    content: str = ""
    tool_calls: List[Dict] = Field(default_factory=list)
    tool_call_id: str = ""
    name: str = ""
    model: str = ""
    metadata: Dict = Field(default_factory=dict)

class CreateInboxItemRequest(BaseModel):
    thread_id: str
    agent_id: str
    tenant_id: str = "tenant-default"
    interrupt_type: str = "generic"
    title: str = ""
    description: str = ""
    data: Dict = Field(default_factory=dict)
    tool_calls: List[Dict] = Field(default_factory=list)
    priority: int = 0
    tags: List[str] = Field(default_factory=list)

class ResolveInboxRequest(BaseModel):
    action: str  # approve, reject, edit, escalate, defer
    response: Optional[Any] = None
    resolved_by: str = ""

class UpdateApiKeysRequest(BaseModel):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    tavily_api_key: str = ""
    snowflake_api_key: str = ""
    pinecone_api_key: str = ""


# ── Register Routes ───────────────────────────────────────────────

def register_v3_routes(app_router, tenant_mgr, gateway, llm_log_mgr,
                       thread_mgr, inbox, api_key_store, workato_reg=None,
                       langfuse_mgr=None, provider_factory_ref=None,
                       model_library_ref=None, integration_manager_ref=None):
    """Register all V3 routes onto the given router."""

    # ═══════════════════════════════════════════════════════════════
    # MULTI-TENANCY
    # ═══════════════════════════════════════════════════════════════

    @app_router.get("/tenants", tags=["Tenants"])
    async def list_tenants():
        tenants = tenant_mgr.list_all()
        return {"count": len(tenants), "tenants": [
            {"tenant_id": t.tenant_id, "name": t.name, "slug": t.slug,
             "tier": t.tier.value, "is_active": t.is_active,
             "owner_email": t.owner_email, "domain": t.domain,
             "current_agents": t.current_agents, "current_users": t.current_users,
             "llm_requests_today": t.llm_requests_today,
             "created_at": t.created_at.isoformat()}
            for t in tenants
        ]}

    @app_router.post("/tenants", tags=["Tenants"])
    async def create_tenant(req: CreateTenantRequest):
        from backend.tenancy.tenant_manager import TenantTier
        t = tenant_mgr.create(
            name=req.name, owner_email=req.owner_email,
            tier=TenantTier(req.tier), domain=req.domain,
            settings=req.settings,
        )
        return {"status": "created", "tenant_id": t.tenant_id, "api_key": t.api_keys[0] if t.api_keys else ""}

    @app_router.get("/tenants/{tenant_id}", tags=["Tenants"])
    async def get_tenant(tenant_id: str):
        t = tenant_mgr.get(tenant_id)
        if not t:
            raise HTTPException(404, "Tenant not found")
        return t.model_dump(mode="json")

    @app_router.put("/tenants/{tenant_id}", tags=["Tenants"])
    async def update_tenant(tenant_id: str, req: UpdateTenantRequest):
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        t = tenant_mgr.update(tenant_id, **updates)
        if not t:
            raise HTTPException(404, "Tenant not found")
        return {"status": "updated", "tenant_id": t.tenant_id}

    @app_router.delete("/tenants/{tenant_id}", tags=["Tenants"])
    async def delete_tenant(tenant_id: str):
        if not tenant_mgr.delete(tenant_id):
            raise HTTPException(404, "Tenant not found")
        return {"status": "deleted"}

    @app_router.get("/tenants/{tenant_id}/usage", tags=["Tenants"])
    async def tenant_usage(tenant_id: str):
        usage = tenant_mgr.get_usage(tenant_id)
        if not usage:
            raise HTTPException(404, "Tenant not found")
        return usage

    @app_router.post("/tenants/{tenant_id}/api-keys", tags=["Tenants"])
    async def generate_tenant_api_key(tenant_id: str):
        key = tenant_mgr.generate_api_key(tenant_id)
        if not key:
            raise HTTPException(400, "Cannot generate API key (quota exceeded or tenant not found)")
        return {"api_key": key}

    @app_router.get("/tenants/stats/summary", tags=["Tenants"])
    async def tenant_stats():
        return tenant_mgr.get_stats()

    # ═══════════════════════════════════════════════════════════════
    # AGENT-AS-A-SERVICE GATEWAY (OpenAI-compatible)
    # ═══════════════════════════════════════════════════════════════

    @app_router.post("/v1/chat/completions", tags=["Agents"])
    async def chat_completions(req: ChatCompletionRequest,
                               authorization: Optional[str] = Header(None)):
        # Resolve tenant from API key
        tenant_id = "tenant-default"
        if authorization and authorization.startswith("Bearer jai-"):
            api_key = authorization.replace("Bearer ", "")
            tenant = tenant_mgr.get_by_api_key(api_key)
            if tenant:
                tenant_id = tenant.tenant_id
            else:
                raise HTTPException(401, "Invalid API key")

        # Check rate limit
        tenant = tenant_mgr.get(tenant_id)
        if tenant and not gateway.check_rate_limit(tenant_id, tenant.quota.llm_requests_per_minute):
            raise HTTPException(429, "Rate limit exceeded")

        from backend.gateway.aaas_gateway import GatewayRequest
        gw_req = GatewayRequest(
            model=req.model, messages=req.messages,
            temperature=req.temperature, max_tokens=req.max_tokens,
            top_p=req.top_p, stream=req.stream,
            agent_id=req.agent_id, tenant_id=tenant_id,
            tools=req.tools, metadata=req.metadata,
        )
        try:
            resp = await gateway.process_completion(
                gw_req, tenant_id, langfuse_manager=langfuse_mgr,
                provider_factory=provider_factory_ref,
                model_library=model_library_ref,
                integration_manager=integration_manager_ref,
            )
            gateway.record_rate_limit(tenant_id)
            if tenant:
                tenant_mgr.record_llm_usage(tenant_id, resp.usage.total_tokens)
            # Log to observability
            llm_log_mgr.log_request(
                tenant_id=tenant_id, agent_id=req.agent_id or "",
                model=resp.model, provider=resp.model.split("-")[0] if "-" in resp.model else "unknown",
                prompt=str(req.messages[-1].get("content", ""))[:200] if req.messages else "",
                response=resp.choices[0].message.get("content", "")[:200] if resp.choices else "",
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                latency_ms=resp.latency_ms, cost_usd=resp.cost_usd,
            )
            return resp.model_dump(mode="json")
        except Exception as e:
            raise HTTPException(500, str(e))

    @app_router.get("/v1/models", tags=["Models"])
    async def list_gateway_models():
        return {"object": "list", "data": [
            {"id": m, "object": "model", "owned_by": "jaggaer"}
            for m in ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro",
                       "claude-sonnet-4-20250514", "claude-3-5-haiku-20241022",
                       "gpt-4o", "gpt-4o-mini"]
        ]}

    @app_router.get("/gateway/stats", tags=["System"])
    async def gateway_stats(tenant_id: Optional[str] = None):
        return gateway.get_stats(tenant_id)

    @app_router.get("/gateway/logs", tags=["System"])
    async def gateway_logs(tenant_id: Optional[str] = None,
                           status: Optional[str] = None,
                           limit: int = Query(default=100, le=500)):
        logs = gateway.get_logs(tenant_id, limit, status)
        return {"count": len(logs), "logs": [l.model_dump(mode="json") for l in logs]}

    # ═══════════════════════════════════════════════════════════════
    # LLM LOGS & DIAGNOSTICS
    # ═══════════════════════════════════════════════════════════════

    @app_router.get("/llm-logs", tags=["System"])
    async def query_llm_logs(tenant_id: Optional[str] = None,
                             agent_id: Optional[str] = None,
                             model: Optional[str] = None,
                             provider: Optional[str] = None,
                             status: Optional[str] = None,
                             thread_id: Optional[str] = None,
                             limit: int = Query(default=100, le=500),
                             offset: int = 0):
        logs = llm_log_mgr.query(
            tenant_id=tenant_id, agent_id=agent_id, model=model,
            provider=provider, status=status, thread_id=thread_id,
            limit=limit, offset=offset,
        )
        return {"count": len(logs), "logs": [l.model_dump(mode="json") for l in logs]}

    @app_router.get("/llm-logs/{log_id}", tags=["System"])
    async def get_llm_log(log_id: str):
        log = llm_log_mgr.get_log(log_id)
        if not log:
            raise HTTPException(404, "Log not found")
        return log.model_dump(mode="json")

    @app_router.get("/llm-logs/diagnostics/summary", tags=["System"])
    async def llm_diagnostics(tenant_id: Optional[str] = None,
                              period_minutes: int = Query(default=60, le=1440)):
        return llm_log_mgr.get_diagnostics(tenant_id, period_minutes).model_dump(mode="json")

    @app_router.get("/llm-logs/stats/summary", tags=["System"])
    async def llm_log_stats():
        return llm_log_mgr.get_stats()

    # ═══════════════════════════════════════════════════════════════
    # THREADS
    # ═══════════════════════════════════════════════════════════════

    @app_router.get("/threads", tags=["Threads"])
    async def list_threads(tenant_id: Optional[str] = None,
                           status: Optional[str] = None,
                           limit: int = Query(default=50, le=200)):
        from backend.threads.thread_manager import ThreadStatus
        s = ThreadStatus(status) if status else None
        threads = thread_mgr.list_all(tenant_id, s, limit)
        return {"count": len(threads), "threads": [
            {"thread_id": t.thread_id, "agent_id": t.agent_id,
             "tenant_id": t.tenant_id, "user_id": t.user_id,
             "title": t.title, "status": t.status.value,
             "message_count": len(t.messages),
             "has_interrupt": t.interrupt is not None and not t.interrupt.get("resolved", False),
             "created_at": t.created_at.isoformat(),
             "updated_at": t.updated_at.isoformat()}
            for t in threads
        ]}

    @app_router.post("/threads", tags=["Threads"])
    async def create_thread(req: CreateThreadRequest):
        thread = thread_mgr.create(
            agent_id=req.agent_id, tenant_id=req.tenant_id,
            user_id=req.user_id, title=req.title, config=req.config,
        )
        return {"status": "created", "thread_id": thread.thread_id}

    @app_router.get("/threads/{thread_id}", tags=["Threads"])
    async def get_thread(thread_id: str):
        thread = thread_mgr.get(thread_id)
        if not thread:
            raise HTTPException(404, "Thread not found")
        return thread.model_dump(mode="json")

    @app_router.get("/threads/{thread_id}/messages", tags=["Threads"])
    async def get_thread_messages(thread_id: str,
                                  limit: int = Query(default=100, le=500),
                                  offset: int = 0):
        msgs = thread_mgr.get_messages(thread_id, limit, offset)
        return {"count": len(msgs), "messages": [m.model_dump(mode="json") for m in msgs]}

    @app_router.post("/threads/{thread_id}/messages", tags=["Threads"])
    async def add_thread_message(thread_id: str, req: AddMessageRequest):
        msg = thread_mgr.add_message(
            thread_id=thread_id, role=req.role, content=req.content,
            tool_calls=req.tool_calls, tool_call_id=req.tool_call_id,
            name=req.name, model=req.model, metadata=req.metadata,
        )
        if not msg:
            raise HTTPException(404, "Thread not found")
        return {"status": "added", "message_id": msg.message_id}

    @app_router.get("/threads/by-agent/{agent_id}", tags=["Threads"])
    async def threads_by_agent(agent_id: str, tenant_id: Optional[str] = None,
                               limit: int = Query(default=50, le=200)):
        threads = thread_mgr.list_by_agent(agent_id, tenant_id, limit)
        return {"count": len(threads), "threads": [
            {"thread_id": t.thread_id, "title": t.title,
             "status": t.status.value, "message_count": len(t.messages),
             "updated_at": t.updated_at.isoformat()}
            for t in threads
        ]}

    @app_router.delete("/threads/{thread_id}", tags=["Threads"])
    async def delete_thread(thread_id: str):
        if not thread_mgr.delete(thread_id):
            raise HTTPException(404, "Thread not found")
        return {"status": "deleted"}

    @app_router.get("/threads/stats/summary", tags=["Threads"])
    async def thread_stats():
        return thread_mgr.get_stats()

    # ═══════════════════════════════════════════════════════════════
    # AGENT INBOX
    # ═══════════════════════════════════════════════════════════════

    @app_router.get("/inbox", tags=["Inbox"])
    async def list_inbox(tenant_id: Optional[str] = None,
                         agent_id: Optional[str] = None,
                         status: Optional[str] = None,
                         limit: int = Query(default=50, le=200),
                         offset: int = 0):
        from backend.inbox.agent_inbox import InboxStatus
        s = InboxStatus(status) if status else None
        items = inbox.list_items(tenant_id, agent_id, s, limit=limit, offset=offset)
        return {"count": len(items), "pending": inbox.count_pending(tenant_id, agent_id),
                "items": [
            {"item_id": i.item_id, "thread_id": i.thread_id,
             "agent_id": i.agent_id, "tenant_id": i.tenant_id,
             "status": i.status.value, "interrupt_type": i.interrupt.type,
             "title": i.interrupt.title, "description": i.interrupt.description,
             "thread_title": i.thread_title, "priority": i.priority,
             "action": i.action.value if i.action else None,
             "created_at": i.created_at.isoformat(),
             "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None}
            for i in items
        ]}

    @app_router.post("/inbox", tags=["Inbox"])
    async def create_inbox_item(req: CreateInboxItemRequest):
        from backend.inbox.agent_inbox import InterruptValue
        interrupt = InterruptValue(
            type=req.interrupt_type, title=req.title,
            description=req.description, data=req.data,
            tool_calls=req.tool_calls,
        )
        item = inbox.create(
            thread_id=req.thread_id, agent_id=req.agent_id,
            interrupt=interrupt, tenant_id=req.tenant_id,
            priority=req.priority, tags=req.tags,
        )
        return {"status": "created", "item_id": item.item_id}

    @app_router.get("/inbox/{item_id}", tags=["Inbox"])
    async def get_inbox_item(item_id: str):
        item = inbox.get(item_id)
        if not item:
            raise HTTPException(404, "Inbox item not found")
        return item.model_dump(mode="json")

    @app_router.post("/inbox/{item_id}/resolve", tags=["Inbox"])
    async def resolve_inbox_item(item_id: str, req: ResolveInboxRequest):
        from backend.inbox.agent_inbox import InboxAction
        item = inbox.resolve(item_id, InboxAction(req.action), req.response, req.resolved_by)
        if not item:
            raise HTTPException(404, "Inbox item not found or already resolved")
        return {"status": "resolved", "item_id": item.item_id, "action": item.action.value}

    @app_router.get("/inbox/stats/summary", tags=["Inbox"])
    async def inbox_stats():
        return inbox.get_stats()

    # ═══════════════════════════════════════════════════════════════
    # SETTINGS — API KEYS (OAP-style per-provider)
    # ═══════════════════════════════════════════════════════════════

    @app_router.get("/settings/api-keys", tags=["System"])
    async def get_api_keys():
        return {"keys": {k: ("*" * 8 + v[-4:] if len(v) > 4 else "") for k, v in api_key_store.items()}}

    @app_router.put("/settings/api-keys", tags=["System"])
    async def update_api_keys(req: UpdateApiKeysRequest):
        for k, v in req.model_dump().items():
            if v:
                api_key_store[k] = v
        return {"status": "updated", "keys_set": [k for k, v in api_key_store.items() if v]}

    @app_router.delete("/settings/api-keys/{key_name}", tags=["System"])
    async def delete_api_key(key_name: str):
        if key_name in api_key_store:
            api_key_store[key_name] = ""
            return {"status": "deleted"}
        raise HTTPException(404, "Key not found")

    # ═══════════════════════════════════════════════════════════════
    # WORKATO CONNECTORS — Enterprise Integration Platform
    # ═══════════════════════════════════════════════════════════════

    @app_router.get("/connectors", tags=["Connectors"])
    async def list_connectors(category: Optional[str] = None, search: Optional[str] = None):
        connectors = workato_reg.list_connectors(category=category, search=search)
        return {"count": len(connectors), "connectors": connectors}

    @app_router.get("/connectors/categories", tags=["Connectors"])
    async def connector_categories():
        return {"categories": workato_reg.get_connector_categories()}

    @app_router.get("/connectors/stats", tags=["Connectors"])
    async def connector_stats():
        return workato_reg.get_stats()

    @app_router.get("/connectors/{connector_id}", tags=["Connectors"])
    async def get_connector(connector_id: str):
        c = workato_reg.get_connector(connector_id)
        if not c:
            raise HTTPException(404, "Connector not found")
        return c

    @app_router.post("/connectors/connections", tags=["Connectors"])
    async def create_connection(req: Request):
        body = await req.json()
        try:
            conn = workato_reg.create_connection(
                connector_id=body["connector_id"],
                name=body.get("name", ""),
                tenant_id=body.get("tenant_id", "tenant-default"),
                auth_config=body.get("auth_config"),
            )
            return {"status": "created", "connection": conn.model_dump()}
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app_router.get("/connectors/connections/list", tags=["Connectors"])
    async def list_connections(tenant_id: Optional[str] = None):
        conns = workato_reg.list_connections(tenant_id=tenant_id)
        return {"count": len(conns), "connections": [c.model_dump() for c in conns]}

    @app_router.post("/connectors/connections/{connection_id}/test", tags=["Connectors"])
    async def test_connection(connection_id: str):
        result = workato_reg.test_connection(connection_id)
        return result

    @app_router.delete("/connectors/connections/{connection_id}", tags=["Connectors"])
    async def delete_connection(connection_id: str):
        if workato_reg.delete_connection(connection_id):
            return {"status": "deleted"}
        raise HTTPException(404, "Connection not found")

    @app_router.post("/connectors/connections/{connection_id}/execute", tags=["Connectors"])
    async def execute_connector_action(connection_id: str, req: Request):
        body = await req.json()
        result = await workato_reg.execute_action(
            connection_id=connection_id,
            action_name=body.get("action_name", ""),
            params=body.get("params"),
        )
        if not result.get("success"):
            raise HTTPException(400, result.get("error", "Action failed"))
        return result

    @app_router.post("/connectors/recipes", tags=["Connectors"])
    async def create_recipe(req: Request):
        body = await req.json()
        recipe = workato_reg.create_recipe(
            name=body["name"],
            connector_id=body["connector_id"],
            connection_id=body["connection_id"],
            trigger_event=body.get("trigger_event"),
            action_name=body.get("action_name"),
            agent_id=body.get("agent_id"),
        )
        return {"status": "created", "recipe": recipe.model_dump()}

    @app_router.get("/connectors/recipes/list", tags=["Connectors"])
    async def list_recipes(connector_id: Optional[str] = None):
        recipes = workato_reg.list_recipes(connector_id=connector_id)
        return {"count": len(recipes), "recipes": [r.model_dump() for r in recipes]}

    @app_router.post("/connectors/recipes/{recipe_id}/toggle", tags=["Connectors"])
    async def toggle_recipe(recipe_id: str):
        recipe = workato_reg.toggle_recipe(recipe_id)
        if not recipe:
            raise HTTPException(404, "Recipe not found")
        return {"status": "toggled", "is_active": recipe.is_active}

    # ═══════════════════════════════════════════════════════════════
    # SEED DATA — Configuration & Templates
    # ═══════════════════════════════════════════════════════════════

    @app_router.get("/seed/settings", tags=["System"])
    async def get_seed_settings():
        from backend.seed.seed_templates import SEED_SETTINGS
        return SEED_SETTINGS

    @app_router.get("/seed/summary", tags=["System"])
    async def get_seed_summary():
        from backend.seed.seed_templates import SEED_AGENTS, SEED_TOOLS, WORKATO_CONNECTORS as WC, SEED_PIPELINES, SEED_PROMPTS
        return {
            "agents": len(SEED_AGENTS),
            "tools": len(SEED_TOOLS),
            "workato_connectors": len(WC),
            "pipelines": len(SEED_PIPELINES),
            "prompts": len(SEED_PROMPTS),
            "agent_categories": list(set(a.get("category") for a in SEED_AGENTS)),
            "tool_categories": list(set(t.get("category") for t in SEED_TOOLS)),
            "connector_categories": list(set(c.get("category") for c in WC)),
        }
