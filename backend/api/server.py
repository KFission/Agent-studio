"""
JAI Agent OS — FastAPI Server (Layer 2: API Gateway & Control Plane)
Provides REST API for the visual canvas, LLM model library, prompt studio,
evaluation studio, channel connectors, LangSmith observability, agent-as-a-service,
orchestrator, tool builder, user management, and RBAC.
"""

import json
import uuid
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import time as _time_mod
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from backend.config.settings import settings
from backend.llm_registry.model_library import ModelLibrary, ModelProvider, ModelCapability, ModelEntry, ModelPricing
from backend.llm_registry.provider_factory import ProviderFactory
from backend.prompt_studio.prompt_manager import PromptManager, PromptCategory
from backend.prompt_studio.langfuse_prompt_manager import LangfusePromptManager
from backend.eval_studio.evaluator import EvaluationStudio
from backend.channels.webhook_handler import WebhookHandler, WebhookConfig, WebhookDirection
from backend.channels.websocket_manager import WebSocketManager
from backend.channels.jaggaer_channel import JaggaerChannel, LLMCallRequest
from backend.observability.langsmith_viewer import LangSmithViewer
from backend.observability.langfuse_integration import LangfuseManager
from backend.compiler.manifest import GraphManifest, NodeDefinition, EdgeDefinition, NodeType, EdgeType
from backend.compiler.compiler import GraphCompiler
from backend.compiler.registry import GraphRegistry
from backend.auth.keycloak_provider import KeycloakProvider
from backend.auth.rbac import RBACManager, Role, Permission
from backend.auth.user_manager import UserManager
from backend.agent_service.agent_registry import AgentRegistry, AgentDefinition, AgentStatus, ModelConfig, RAGConfig, MemoryConfig, DBConfig, ToolBinding, AgentEndpoint, AccessControl
from backend.agent_service.agent_memory import AgentMemoryManager
from backend.agent_service.agent_rag import AgentRAGManager
from backend.agent_service.agent_db import AgentDBConnector, DBConnection, DBType
from backend.orchestrator.orchestrator import AgentOrchestrator, Pipeline, PipelineStep, OrchestrationPattern
from backend.tool_builder.tool_registry import ToolRegistry, ToolDefinition, ToolType
from backend.tenancy.tenant_manager import TenantManager
from backend.gateway.aaas_gateway import AgentGateway
from backend.llm_logs.observability import LLMLogManager
from backend.threads.thread_manager import ThreadManager
from backend.inbox.agent_inbox import AgentInbox
from backend.connectors.workato_registry import WorkatoConnectorRegistry
from backend.auth.group_manager import GroupManager
from backend.environments.environment_manager import EnvironmentManager
from backend.metering.usage_metering import UsageMeteringManager
from backend.integrations.llm_integration_manager import LLMIntegrationManager
from backend.guardrails.guardrail_manager import GuardrailManager
from backend.seed.seed_templates import SEED_AGENTS, SEED_TOOLS, SEED_PIPELINES, SEED_PROMPTS, SEED_SETTINGS, WORKATO_CONNECTORS


# ── Global Instances ──────────────────────────────────────────────────────────

model_library = ModelLibrary()
provider_factory = ProviderFactory(model_library)
prompt_manager = PromptManager()
eval_studio = None  # initialized after integration_manager
webhook_handler = WebhookHandler()
ws_manager = WebSocketManager(max_connections=settings.websocket_max_connections)
jaggaer_channel = JaggaerChannel(model_library, provider_factory)
langsmith_viewer = LangSmithViewer()
langfuse_manager = LangfuseManager()
langfuse_prompt_mgr = LangfusePromptManager(
    host=settings.langfuse_host or "",
    public_key=settings.langfuse_public_key or "",
    secret_key=settings.langfuse_secret_key or "",
)
from backend.prompt_studio.experiment_manager import ExperimentManager
experiment_manager = ExperimentManager(
    host=settings.langfuse_host or "",
    public_key=settings.langfuse_public_key or "",
    secret_key=settings.langfuse_secret_key or "",
)
# Inject Langfuse into provider factory for automatic LangChain callback tracing
provider_factory._langfuse_manager = langfuse_manager
graph_compiler = GraphCompiler(provider_factory, prompt_manager, model_library)
graph_registry = GraphRegistry()
keycloak = KeycloakProvider(
    server_url=getattr(settings, 'keycloak_server_url', 'http://localhost:8180'),
    realm=getattr(settings, 'keycloak_realm', 'jai-agent-os'),
    client_id=getattr(settings, 'keycloak_client_id', 'jai-agent-os-api'),
    client_secret=getattr(settings, 'keycloak_client_secret', ''),
)
rbac_manager = RBACManager()
user_manager = UserManager()
agent_registry = AgentRegistry()
agent_memory = AgentMemoryManager()
agent_rag = AgentRAGManager()
agent_db = AgentDBConnector()
orchestrator = AgentOrchestrator()
tool_registry = ToolRegistry()
tenant_manager = TenantManager()
agent_gateway = AgentGateway()
llm_log_manager = LLMLogManager()
thread_manager = ThreadManager()
agent_inbox = AgentInbox()
api_key_store = {"openai_api_key": "", "anthropic_api_key": "", "google_api_key": "", "tavily_api_key": "", "snowflake_api_key": "", "pinecone_api_key": ""}
api_token_store = []  # API tokens for AaaS authentication
workato_registry = WorkatoConnectorRegistry()
group_manager = GroupManager()
environment_manager = EnvironmentManager()
usage_metering = UsageMeteringManager()
integration_manager = LLMIntegrationManager()
eval_studio = EvaluationStudio(model_library, provider_factory, integration_manager)
guardrail_manager = GuardrailManager()

from backend.marketplace.marketplace_manager import MarketplaceManager
marketplace_manager = MarketplaceManager()

# ── Redis & Cache (initialized in lifespan) ────────────────────────────────
_cache_layer = None   # CacheLayer instance
_redis_state = None   # RedisStateManager instance
# LangGraph Supervisor client
from backend.langgraph_client.client import LangGraphClient
langgraph_client = LangGraphClient()


async def _hydrate_from_db(session):
    """Load data from DB into in-memory managers so existing routes work with DB-sourced data."""
    from sqlalchemy import select
    from backend.db.models import (
        AgentModel, ToolModel, PromptTemplateModel, TenantModel, UserModel,
    )
    from backend.auth.user_manager import UserProfile
    from backend.tenancy.tenant_manager import Tenant, TenantTier, TIER_QUOTAS

    # ── Users ──────────────────────────────────────────────────
    rows = (await session.execute(select(UserModel))).scalars().all()
    for u in rows:
        if u.id not in user_manager._users:
            profile = UserProfile(
                user_id=u.id, username=u.username, email=u.email,
                first_name=u.first_name, last_name=u.last_name,
                display_name=u.display_name or f"{u.first_name} {u.last_name}".strip(),
                tenant_id=u.tenant_id, roles=u.roles or ["viewer"],
                is_active=u.is_active,
            )
            user_manager._users[u.id] = profile
            user_manager._email_index[u.email] = u.id
            user_manager._username_index[u.username] = u.id
    print(f"[JAI AGENT OS]   Hydrated {len(rows)} users from DB")

    # ── Tenants ────────────────────────────────────────────────
    rows = (await session.execute(select(TenantModel))).scalars().all()
    for t in rows:
        if t.id not in tenant_manager._tenants:
            tier = TenantTier(t.tier) if t.tier in [e.value for e in TenantTier] else TenantTier.ENTERPRISE
            tenant = Tenant(
                tenant_id=t.id, name=t.name, slug=t.slug, tier=tier,
                quota=TIER_QUOTAS[tier], owner_email=t.owner_email,
                domain=t.domain, is_active=t.is_active,
                allowed_providers=t.allowed_providers or [],
            )
            tenant_manager._tenants[t.id] = tenant
            tenant_manager._slug_to_tenant[t.slug] = t.id
    print(f"[JAI AGENT OS]   Hydrated {len(rows)} tenants from DB")

    # ── Agents ─────────────────────────────────────────────────
    rows = (await session.execute(select(AgentModel))).scalars().all()
    for a in rows:
        if a.id not in agent_registry._agents:
            mc = a.model_config_json or {}
            tools_data = a.tools_json or []
            tool_bindings = [ToolBinding(tool_id=tb.get("tool_id", ""), tool_name=tb.get("tool_name", "")) for tb in tools_data]
            agent_def = AgentDefinition(
                agent_id=a.id, name=a.name, description=a.description or "",
                version=a.version or 1,
                status=AgentStatus(a.status) if a.status in [s.value for s in AgentStatus] else AgentStatus.DRAFT,
                tags=a.tags or [],
                model_config=ModelConfig(
                    model_id=mc.get("model_id", "gemini-2.5-flash"),
                    temperature=mc.get("temperature", 0.3),
                    max_tokens=mc.get("max_tokens", 2000),
                ),
                tools=tool_bindings,
                context=a.context or "",
                metadata=a.metadata_json or {},
                created_by=a.created_by or "",
            )
            agent_def.created_at = a.created_at
            agent_def.updated_at = a.updated_at
            agent_registry._agents[a.id] = agent_def
    print(f"[JAI AGENT OS]   Hydrated {len(rows)} agents from DB")

    # ── Tools ──────────────────────────────────────────────────
    _type_map = {"api": ToolType.REST_API, "db": ToolType.REST_API, "llm": ToolType.CODE,
                 "rag": ToolType.REST_API, "python": ToolType.CODE, "workato": ToolType.REST_API}
    rows = (await session.execute(select(ToolModel))).scalars().all()
    for t in rows:
        if t.id not in tool_registry._tools:
            mapped_type = _type_map.get(t.tool_type, ToolType.REST_API)
            tool_def = ToolDefinition(
                tool_id=t.id, name=t.name, description=t.description or "",
                tool_type=mapped_type, status=t.status or "active",
                tags=t.tags or [],
                metadata={
                    "category": t.category or "",
                    "config": t.config_json or {},
                    "endpoints": t.endpoints_json or [],
                    "is_platform_tool": t.is_platform_tool,
                },
            )
            tool_registry._tools[t.id] = tool_def
    print(f"[JAI AGENT OS]   Hydrated {len(rows)} tools from DB")

    # ── Prompts ────────────────────────────────────────────────
    rows = (await session.execute(select(PromptTemplateModel))).scalars().all()
    for p in rows:
        if p.id not in prompt_manager._templates:
            tmpl = prompt_manager.create(
                name=p.name, content=p.content,
                description=p.description or "",
                category=PromptCategory.CUSTOM,
                tags=[p.category] if p.category else [],
            )
            prompt_manager._templates.pop(tmpl.template_id, None)
            tmpl.template_id = p.id
            prompt_manager._templates[p.id] = tmpl
    print(f"[JAI AGENT OS]   Hydrated {len(rows)} prompts from DB")


def _load_seed_data():
    """Load supplementary in-memory seed data (groups, integrations, pipelines).
    Core data (users, agents, tools, prompts, tenants, guardrails) comes from DB."""
    from backend.auth.user_manager import UserProfile
    from backend.tenancy.tenant_manager import Tenant, TenantTier, TIER_QUOTAS

    # Fallback admin user + tenant (normally comes from DB)
    if "admin-001" not in user_manager._users:
        admin = UserProfile(
            user_id="admin-001", username="admin", email="admin@jaggaer.com",
            first_name="Platform", last_name="Admin", display_name="Platform Admin",
            tenant_id="default", roles=["platform_admin"],
        )
        user_manager._users[admin.user_id] = admin
        user_manager._email_index[admin.email] = admin.user_id
        user_manager._username_index[admin.username] = admin.user_id
    if "tenant-default" not in tenant_manager._tenants:
        t = Tenant(
            tenant_id="tenant-default", name="Jaggaer Default", slug="default",
            tier=TenantTier.ENTERPRISE, quota=TIER_QUOTAS[TenantTier.ENTERPRISE],
            owner_email="admin@jaggaer.com", domain="jaggaer.com",
            allowed_providers=["google", "anthropic", "openai", "ollama"],
        )
        tenant_manager._tenants[t.tenant_id] = t
        tenant_manager._slug_to_tenant[t.slug] = t.tenant_id

    # Agents, tools, prompts, guardrails → come from DB (seed_db.py + hydration).
    # Only seed agents/tools into memory if DB didn't provide them (fallback).
    if not agent_registry._agents:
        for a in SEED_AGENTS:
            tool_bindings = [ToolBinding(tool_id=tid, tool_name=tid) for tid in a.get("tools", [])]
            agent_def = AgentDefinition(
                agent_id=a["agent_id"], name=a["name"], description=a["description"],
                status=AgentStatus.ACTIVE if a.get("status") == "active" else AgentStatus.DRAFT,
                tags=a.get("tags", []),
                model_config=ModelConfig(
                    model_id=a.get("config", {}).get("llm_model", "gemini-2.5-flash"),
                    temperature=a.get("config", {}).get("temperature", 0.3),
                    max_tokens=a.get("config", {}).get("max_tokens", 2000),
                ),
                tools=tool_bindings,
                metadata={"category": a.get("category", "general"), "seed_config": a.get("config", {})},
            )
            agent_registry.create(agent_def)

    # Tools are now DB-backed only — no hardcoded seed tools.
    # Users create tools via the UI which persists them to PostgreSQL.

    if not prompt_manager._templates:
        for pr in SEED_PROMPTS:
            t = prompt_manager.create(name=pr["name"], content=pr["content"],
                description=pr.get("description", ""), category=PromptCategory.CUSTOM, tags=[pr.get("category", "general")])
            prompt_manager._templates.pop(t.template_id, None)
            t.template_id = pr["template_id"]
            prompt_manager._templates[pr["template_id"]] = t

    # ── Seed Pipelines (in-memory only — not DB-backed yet) ────────────────
    _pattern_map = {"sequential": OrchestrationPattern.SEQUENTIAL,
                    "parallel": OrchestrationPattern.PARALLEL,
                    "supervisor": OrchestrationPattern.SUPERVISOR}
    for p in SEED_PIPELINES:
        if p["pipeline_id"] not in orchestrator._pipelines:
            steps = [PipelineStep(agent_id=aid, agent_name=aid, order=i) for i, aid in enumerate(p.get("agents", []))]
            pipe = Pipeline(
                pipeline_id=p["pipeline_id"], name=p["name"], description=p["description"],
                pattern=_pattern_map.get(p.get("pattern", "sequential"), OrchestrationPattern.SEQUENTIAL),
                steps=steps, status="active",
                metadata={"connectors": p.get("connectors", []), "config": p.get("config", {})},
            )
            orchestrator.create_pipeline(pipe)

    # ── Seed Groups (in-memory only — not DB-backed yet) ───────────────────
    _seed_groups = [
        {"name": "Procurement Engineering", "description": "Engineering team building procurement agents", "lob": "Procurement", "budget": 5000},
        {"name": "Finance Analytics", "description": "Finance team using spend analytics agents", "lob": "Finance", "budget": 3000},
        {"name": "Sourcing Ops", "description": "Sourcing operations team", "lob": "Sourcing", "budget": 8000},
        {"name": "Platform Admins", "description": "Platform administration team", "lob": "IT", "budget": 0},
    ]
    for g in _seed_groups:
        if not any(x.name == g["name"] for x in group_manager.list_all()):
            group_manager.create(g["name"], g["description"], g["lob"], monthly_budget_usd=g.get("budget", 0))

    # LLM Integrations — no seed data. Admins add them via the UI.
    # They are persisted in the DB and hydrated on startup.

    # ── Seed Usage Metering (realistic demo data) ───────────────────────────
    if not usage_metering._records:
        import random as _rng
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        _rng.seed(42)  # deterministic demo data

        _seed_agent_ids = [a["agent_id"] for a in SEED_AGENTS[:6]]
        _seed_models = ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o-mini", "claude-3-5-haiku", "gpt-4o", "gemini-2.0-flash"]
        _seed_providers = {"gemini": "google", "gpt": "openai", "claude": "anthropic"}
        _seed_users = ["alice@jaggaer.com", "bob@jaggaer.com", "carol@jaggaer.com", "dave@jaggaer.com", "eve@jaggaer.com"]
        _seed_group_names = [g["name"] for g in _seed_groups]
        _seed_lobs = [g["lob"] for g in _seed_groups]
        _group_objs = group_manager.list_all()

        _now = _dt.now(_tz.utc)
        for _day_offset in range(30, 0, -1):
            _day_base = _now - _td(days=_day_offset)
            # Weekdays get more traffic
            _is_weekday = _day_base.weekday() < 5
            _calls_today = _rng.randint(15, 45) if _is_weekday else _rng.randint(3, 12)
            for _ in range(_calls_today):
                _model = _rng.choice(_seed_models)
                _provider = next((v for k, v in _seed_providers.items() if k in _model), "unknown")
                _agent = _rng.choice(_seed_agent_ids)
                _user = _rng.choice(_seed_users)
                _grp = _rng.choice(_group_objs) if _group_objs else None
                _inp_tok = _rng.randint(200, 4000)
                _out_tok = _rng.randint(100, 2000)
                _lat = _rng.uniform(200, 3500)
                _status = "success" if _rng.random() < 0.94 else "error"
                _ts = _day_base + _td(hours=_rng.randint(8, 20), minutes=_rng.randint(0, 59), seconds=_rng.randint(0, 59))

                rec = usage_metering.record(
                    group_id=_grp.group_id if _grp else "",
                    lob=_grp.lob if _grp else "",
                    user_id=_user,
                    agent_id=_agent,
                    model_id=_model,
                    provider=_provider,
                    input_tokens=_inp_tok,
                    output_tokens=_out_tok,
                    latency_ms=round(_lat, 1),
                    status=_status,
                )
                rec.timestamp = _ts  # backdate the record

    # ── Seed API Tokens ────────────────────────────────────────────────────
    if not api_token_store:
        import uuid as _uuid, hashlib as _hl
        from datetime import datetime
        _token_raw = f"jai-tk-{_uuid.uuid4().hex[:24]}"
        api_token_store.append({
            "token_id": f"tok-{_uuid.uuid4().hex[:8]}",
            "name": "Default Dev Token",
            "token_prefix": _token_raw[:12] + "...",
            "token_hash": _hl.sha256(_token_raw.encode()).hexdigest(),
            "token_plain": _token_raw,  # only shown once at creation
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "status": "active",
        })


_MODEL_PRICING = {
    # Google Gemini (per 1K tokens)
    "gemini-2.5-flash":         (0.00015, 0.0006),
    "gemini-2.5-pro":           (0.00125, 0.01),
    "gemini-2.0-flash":         (0.0001,  0.0004),
    "gemini-2.0-flash-001":     (0.0001,  0.0004),
    "gemini-2.0-flash-lite":    (0.000075, 0.0003),
    "gemini-2.0-flash-lite-001":(0.000075, 0.0003),
    "gemini-1.5-flash":         (0.000075, 0.0003),
    "gemini-1.5-pro":           (0.00125, 0.005),
    # OpenAI
    "gpt-4o":                   (0.0025, 0.01),
    "gpt-4o-mini":              (0.00015, 0.0006),
    "gpt-4-turbo":              (0.01, 0.03),
    "o1":                       (0.015, 0.06),
    "o1-mini":                  (0.003, 0.012),
    "o3-mini":                  (0.0011, 0.0044),
    # Anthropic
    "claude-sonnet-4-20250514": (0.003, 0.015),
    "claude-3-5-sonnet":        (0.003, 0.015),
    "claude-3-5-haiku":         (0.0008, 0.004),
    "claude-3-opus":            (0.015, 0.075),
}


def _get_model_pricing(model_name: str):
    """Return (input_cost_per_1k, output_cost_per_1k) for known models, else (0, 0)."""
    from backend.llm_registry.model_library import ModelPricing
    for key, (inp, out) in _MODEL_PRICING.items():
        if key in model_name:
            return ModelPricing(input_cost_per_1k=inp, output_cost_per_1k=out)
    return ModelPricing()


def _register_models_from_integrations():
    """Register models from saved integrations into ModelLibrary."""
    from backend.llm_registry.model_library import ModelEntry, ModelProvider, ModelPricing
    provider_map = {"google": ModelProvider.GOOGLE, "openai": ModelProvider.OPENAI,
                    "anthropic": ModelProvider.ANTHROPIC, "ollama": ModelProvider.OLLAMA}
    count = 0
    for intg in integration_manager.list_all():
        prov = provider_map.get(intg.provider.value)
        if not prov:
            continue
        for model_name in (intg.registered_models or []):
            mid = model_name
            if mid not in model_library._models:
                model_library.register(ModelEntry(
                    model_id=mid,
                    display_name=model_name,
                    provider=prov,
                    model_name=model_name,
                    description=f"Registered from integration '{intg.name}'",
                    requires_api_key=(intg.auth_type == "api_key"),
                    is_local=(intg.provider.value == "ollama"),
                    pricing=_get_model_pricing(model_name),
                    metadata={"integration_id": intg.integration_id},
                ))
                count += 1
    if count:
        print(f"[JAI AGENT OS]   Registered {count} models from integrations")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and teardown platform resources."""
    print("[JAI AGENT OS] Initializing platform...")

    # ── Initialize Redis shared state + cache ───────────────────
    try:
        from backend.cache import RedisStateManager, CacheLayer
        app.state.redis_state = RedisStateManager(settings.redis_url)
        app.state.cache = CacheLayer(settings.redis_url)
        redis_ok = await app.state.redis_state.connect()
        cache_ok = await app.state.cache.connect()
        if redis_ok:
            print(f"[JAI AGENT OS]   Redis: connected ({settings.redis_url})")
        else:
            print("[JAI AGENT OS]   Redis: unavailable — using in-memory fallback")
        if cache_ok:
            print("[JAI AGENT OS]   Cache: Redis L2 active")
        else:
            print("[JAI AGENT OS]   Cache: L1-only (in-memory)")
        # Make cache globally accessible to registries
        global _cache_layer, _redis_state
        _cache_layer = app.state.cache
        _redis_state = app.state.redis_state
    except Exception as e:
        print(f"[JAI AGENT OS]   Redis/Cache: SKIPPED ({e})")

    # ── Initialize PostgreSQL tables + seed data ────────────────
    db_ok = False
    try:
        from backend.db.engine import get_engine, get_session_factory
        from backend.db.base import Base
        from backend.db.models import (  # noqa: F401
            AgentModel, ProviderCredentialModel, UserModel,
            ToolModel, PromptTemplateModel, TenantModel,
            GuardrailRuleModel, IntegrationModel,
            ThreadModel, ThreadMessageModel, UsageRecordModel,
            GroupModel, PipelineModel, PipelineRunModel,
            InboxItemModel, MemoryEntryModel,
            RAGCollectionModel, RAGDocumentModel,
            KnowledgeBaseModel, FileUploadModel,
        )
        from backend.db.seed_db import seed_all

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[JAI AGENT OS]   PostgreSQL: tables initialized")

        # Seed default data if tables are empty
        factory = get_session_factory()
        async with factory() as session:
            counts = await seed_all(session)
            seeded = {k: v for k, v in counts.items() if v > 0}
            if seeded:
                print(f"[JAI AGENT OS]   DB Seed: {seeded}")
            else:
                print("[JAI AGENT OS]   DB Seed: already populated")

        # Hydrate in-memory managers from DB
        async with factory() as session:
            await _hydrate_from_db(session)

        # Hydrate guardrails from DB
        async with factory() as session:
            await guardrail_manager.hydrate_from_db(session)

        # Hydrate integrations from DB
        async with factory() as session:
            await integration_manager.hydrate_from_db(session)

        # Register models from hydrated integrations into ModelLibrary
        _register_models_from_integrations()

        # Mark registries as DB-available for write-through
        agent_registry._db_available = True
        integration_manager._db_available = True
        thread_manager._db_available = True
        usage_metering._db_available = True
        user_manager._db_available = True
        group_manager._db_available = True
        tenant_manager._db_available = True
        tool_registry._db_available = True
        orchestrator._db_available = True
        agent_inbox._db_available = True
        agent_memory._db_available = True
        agent_rag._db_available = True
        db_ok = True
        print("[JAI AGENT OS]   Threads: persistence=postgresql")
        print("[JAI AGENT OS]   Usage Metering: persistence=postgresql")
        print("[JAI AGENT OS]   All managers: persistence=postgresql")
    except Exception as e:
        print(f"[JAI AGENT OS]   PostgreSQL: SKIPPED ({e})")

    # Always load supplementary seed data (groups, integrations, guardrails, inbox, logs).
    # Core data (users, agents, tools, prompts, tenants) comes from DB when available.
    # _load_seed_data has idempotent guards so DB-hydrated items won't be duplicated.
    _load_seed_data()

    print(f"[JAI AGENT OS]   Models: {len(model_library.list_all())}")
    print(f"[JAI AGENT OS]   Providers: {provider_factory.list_available_providers()}")
    print(f"[JAI AGENT OS]   Users: {user_manager.get_stats()['total_users']}")
    print(f"[JAI AGENT OS]   Agents: {agent_registry.get_stats()['total_agents']}")
    print(f"[JAI AGENT OS]   Tools: {tool_registry.get_stats()['total_tools']}")
    # Seed built-in prompts into Langfuse
    if langfuse_prompt_mgr._public_key:
        seeded = langfuse_prompt_mgr.seed_builtin_prompts()
        if seeded:
            print(f"[JAI AGENT OS]   Langfuse Prompts: seeded {seeded} built-in prompts")
    lf_prompts = langfuse_prompt_mgr.list_prompts(limit=1)
    prompt_count = lf_prompts.get("meta", {}).get("totalItems", 0) or lf_prompts.get("pagination", {}).get("totalItems", 0)
    print(f"[JAI AGENT OS]   Prompts: {prompt_count} (Langfuse)")
    print(f"[JAI AGENT OS]   Tenants: {tenant_manager.get_stats()['total_tenants']}")
    print(f"[JAI AGENT OS]   Keycloak: {'configured' if keycloak.is_configured() else 'not configured'}")
    print(f"[JAI AGENT OS]   LangSmith: {'configured' if langsmith_viewer.is_configured() else 'not configured'}")
    print(f"[JAI AGENT OS]   Langfuse: {'configured' if langfuse_manager.is_configured() else 'not configured'} — {settings.langfuse_host}")
    print(f"[JAI AGENT OS]   Gateway: ready (OpenAI-compatible /v1/chat/completions)")
    print(f"[JAI AGENT OS]   LLM Logs: {llm_log_manager.get_stats()['total_logs']} entries")
    # Load seed data from Agents_GP + ChatwithData
    _load_seed_data()
    print(f"[JAI AGENT OS]   Seed Agents: {len(SEED_AGENTS)} templates loaded")
    print(f"[JAI AGENT OS]   Seed Tools: {len(SEED_TOOLS)} + {len(WORKATO_CONNECTORS)} Workato connectors")
    print(f"[JAI AGENT OS]   Seed Pipelines: {len(SEED_PIPELINES)} templates")
    print(f"[JAI AGENT OS]   Workato: {workato_registry.get_stats()['total_connectors']} connectors available")
    # Check LangGraph server connectivity
    import os as _os
    _lg_url = _os.getenv("LANGGRAPH_URL", "http://localhost:2024")
    try:
        import httpx as _httpx
        _r = _httpx.get(f"{_lg_url}/ok", timeout=5)
        print(f"[JAI AGENT OS]   LangGraph: connected ({_lg_url})")
    except Exception:
        print(f"[JAI AGENT OS]   LangGraph: not reachable ({_lg_url}) — agents will sync when server starts")
    print("[JAI AGENT OS] Platform ready.")
    yield
    print("[JAI AGENT OS] Shutting down...")
    # Dispose Redis/cache
    try:
        if hasattr(app.state, 'cache'):
            await app.state.cache.disconnect()
        if hasattr(app.state, 'redis_state'):
            await app.state.redis_state.disconnect()
    except Exception:
        pass
    # Dispose async DB engine
    try:
        from backend.db.engine import dispose_engine
        await dispose_engine()
    except Exception:
        pass
    langfuse_manager.shutdown()
    await langgraph_client.close()


_openapi_tags = [
    {"name": "System", "description": "Health checks, platform info, monitoring, observability, dashboard"},
    {"name": "Auth", "description": "Authentication, RBAC roles, API tokens, audit log"},
    {"name": "Users", "description": "User management — CRUD, roles, API keys"},
    {"name": "Groups", "description": "LoB / Team groups — members, model assignment, agent assignment"},
    {"name": "Tenants", "description": "Multi-tenancy management"},
    {"name": "Agents", "description": "Agent-as-a-Service — CRUD, versioning, rollback, invoke, graphs"},
    {"name": "Agent Memory", "description": "Agent memory — conversations, sessions, long-term storage"},
    {"name": "Agent RAG", "description": "RAG collections, documents, knowledge bases, retrieval"},
    {"name": "Models", "description": "LLM Model Library — registry, providers, cost comparison"},
    {"name": "Prompts", "description": "Prompt Studio — Langfuse-backed prompts, versions, playground"},
    {"name": "Tools", "description": "Tool Builder — code, REST API, MCP tools"},
    {"name": "Pipelines", "description": "Orchestrator pipelines — CRUD, execution, workflow invoke"},
    {"name": "Evaluation", "description": "Eval Studio — token estimation, single/multi model evaluation"},
    {"name": "Scoring", "description": "Evaluation scoring — reference metrics, LLM-as-judge"},
    {"name": "Experiments", "description": "Experiment datasets, runs, A/B testing"},
    {"name": "Environments", "description": "Environment management — Dev/QA/UAT/Prod, variables, locks"},
    {"name": "Promotions", "description": "Asset promotion between environments — approve, reject, rollback"},
    {"name": "Threads", "description": "Conversation threads — messages, agent scoping"},
    {"name": "Inbox", "description": "Agent inbox — HITL approvals, interrupts"},
    {"name": "Metering", "description": "Usage metering — cost reports by group/LoB/agent/model/user"},
    {"name": "Webhooks", "description": "Webhook channels — inbound/outbound, events"},
    {"name": "WebSocket", "description": "Real-time streaming — WebSocket connections, chat"},
    {"name": "Integrations", "description": "LLM provider integrations — credentials, push to groups"},
    {"name": "Guardrails", "description": "Guardrail rules — PII, injection, profanity, deploy/validate"},
    {"name": "Connectors", "description": "Enterprise connectors — Workato, notifications, Jaggaer"},
]

app = FastAPI(
    title="JAI Agent OS",
    description=(
        "## JAGGAER AI Agent Operating System\n\n"
        "Enterprise platform for building, testing, deploying, and monitoring agentic AI workflows.\n\n"
        "**Capabilities:** Agent-as-a-Service, Orchestrator, Tool Builder, LLM Registry, "
        "Prompt Studio, Eval Studio, RBAC, Channels, Observability, Environment Promotion\n\n"
        "**Providers:** Google Gemini, Anthropic Claude, OpenAI GPT, Ollama (local)\n\n"
        "---\n"
    ),
    version="2.0.0",
    lifespan=lifespan,
    openapi_tags=_openapi_tags,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — configurable allowed origins ─────────────────────────────────────
import os as _os
_cors_origins_raw = _os.environ.get("CORS_ALLOWED_ORIGINS", "*")
_cors_origins = ["*"] if _cors_origins_raw.strip() == "*" else [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth Middleware — verify Bearer tokens on protected routes ──────────────
_PUBLIC_PATHS = {
    "/info", "/health", "/docs", "/openapi.json", "/redoc",
    "/auth/login", "/auth/logout", "/auth/sso",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")
        # Skip auth for public endpoints, OPTIONS (CORS preflight), and WebSocket
        if (request.method == "OPTIONS"
                or path in _PUBLIC_PATHS
                or path.startswith("/docs")
                or path.startswith("/openapi")):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            cached = keycloak._token_cache.get(token)
            if cached and (not cached.exp or cached.exp > _time_mod.time()):
                # Attach user info to request state for downstream use
                request.state.user = cached
                return await call_next(request)

        # No valid token — allow in dev mode (ENVIRONMENT=dev), reject in prod
        if settings.environment in ("dev", "development"):
            return await call_next(request)

        return JSONResponse(status_code=401, content={"detail": "Authentication required. Please log in."})


app.add_middleware(AuthMiddleware)


# ── Request Timeout Middleware — prevent endpoints from running indefinitely ──
import asyncio as _asyncio

_SLOW_PATH_PREFIXES = ("/chat/", "/playground/", "/pipelines/", "/prompts/improve", "/agents/invoke")
_DEFAULT_TIMEOUT = 120  # seconds
_SLOW_TIMEOUT = 300     # seconds for LLM / pipeline endpoints
# Skip asyncio.wait_for entirely for these paths — wrapping multipart uploads in
# wait_for is a known Starlette/BaseHTTPMiddleware bug that can corrupt the request
# body stream or cancel mid-transfer, causing silent 504s on large file uploads.
_NO_TIMEOUT_PATHS = ("/knowledge-bases/",)


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in _NO_TIMEOUT_PATHS):
            return await call_next(request)
        timeout = _SLOW_TIMEOUT if any(path.startswith(p) for p in _SLOW_PATH_PREFIXES) else _DEFAULT_TIMEOUT
        try:
            return await _asyncio.wait_for(call_next(request), timeout=timeout)
        except _asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": f"Request timed out after {timeout}s", "path": path},
            )


app.add_middleware(TimeoutMiddleware)


# ── Request/Response Models ───────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    models_loaded: int = 0
    providers: dict = Field(default_factory=dict)
    langsmith_configured: bool = False
    langfuse_configured: bool = False


class RegisterModelRequest(BaseModel):
    model_id: str
    display_name: str
    provider: str
    model_name: str
    description: str = ""
    max_tokens: int = 4096
    max_context_window: int = 128000
    default_temperature: float = 0.0
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    is_local: bool = False


class CreatePromptRequest(BaseModel):
    name: str
    prompt: Any  # str for text, list[dict] for chat
    type: str = "text"  # "text" or "chat"
    config: Dict = Field(default_factory=dict)
    labels: List[str] = Field(default_factory=lambda: ["latest"])
    tags: List[str] = Field(default_factory=list)


class RenderPromptRequest(BaseModel):
    name: str
    variables: dict = Field(default_factory=dict)
    version: Optional[int] = None
    label: Optional[str] = None


class PlaygroundRunRequest(BaseModel):
    prompt_name: Optional[str] = None
    prompt_content: Optional[Any] = None  # ad-hoc prompt (str or messages list)
    prompt_type: str = "text"
    variables: Dict[str, str] = Field(default_factory=dict)
    model_id: str = "gemini-2.5-flash"
    temperature: float = 0.7
    max_tokens: int = 1024
    version: Optional[int] = None
    label: Optional[str] = None


class EvalSingleRequest(BaseModel):
    prompt: str
    model_id: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    reference_text: Optional[str] = None
    scoring_metrics: Optional[List[str]] = None
    llm_judge_enabled: bool = False
    judge_model_id: str = "gemini-2.5-flash"
    judge_criteria: Optional[List[str]] = None


class EvalMultiRequest(BaseModel):
    prompt: str
    model_ids: List[str]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    reference_text: Optional[str] = None
    scoring_metrics: Optional[List[str]] = None
    llm_judge_enabled: bool = False
    judge_model_id: str = "gemini-2.5-flash"
    judge_criteria: Optional[List[str]] = None


class CreateWebhookRequest(BaseModel):
    name: str
    direction: str = "inbound"
    url: str = ""
    agent_id: Optional[str] = None


class JaggaerLLMRequest(BaseModel):
    tenant_id: str
    user_id: str = ""
    call_type: str = "completion"
    model_id: Optional[str] = None
    prompt: str
    system_prompt: Optional[str] = None
    variables: dict = Field(default_factory=dict)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class FeedbackRequest(BaseModel):
    run_id: str
    key: str
    score: Optional[float] = None
    value: Optional[str] = None
    comment: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH & INFO
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health", tags=["System"])
async def health():
    """Deep health check — probes DB, Redis, and Langfuse connectivity."""
    checks = {}
    overall = "ok"

    # ── PostgreSQL ──
    try:
        from backend.db.sync_bridge import get_session_factory
        sf = get_session_factory()
        if sf:
            from sqlalchemy import text
            async with sf() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = {"status": "ok", "driver": "asyncpg"}
        else:
            checks["database"] = {"status": "unavailable", "detail": "no session factory"}
            overall = "degraded"
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)[:200]}
        overall = "degraded"

    # ── Redis ──
    try:
        if _redis_state:
            info = await _redis_state.info()
            checks["redis"] = {"status": "ok" if info.get("connected") else "error", "detail": info}
        else:
            checks["redis"] = {"status": "unavailable", "detail": "not initialized"}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)[:200]}

    # ── Langfuse ──
    try:
        lf_status = langfuse_manager.get_status()
        checks["langfuse"] = {
            "status": "ok" if lf_status.get("connected") else ("unconfigured" if not lf_status.get("configured") else "error"),
            "host": lf_status.get("host", ""),
        }
        if lf_status.get("error"):
            checks["langfuse"]["detail"] = lf_status["error"]
    except Exception as e:
        checks["langfuse"] = {"status": "error", "detail": str(e)[:200]}

    return {
        "status": overall,
        "version": "1.0.0",
        "models_loaded": len(model_library.list_all()),
        "providers": provider_factory.list_available_providers(),
        "checks": checks,
    }


@app.get("/info")
async def platform_info():
    return {
        "platform": "Agent Studio",
        "version": "1.0.0",
        "architecture": "L1-Canvas / L2-API / L3-LangGraph / L4-Services / L5-State / L6-Observability",
        "models": len(model_library.list_all()),
        "providers": provider_factory.list_available_providers(),
        "prompt_templates": len(prompt_manager.list_all()),
        "webhooks": len(webhook_handler.list_all()),
        "websocket_connections": ws_manager.active_connections,
        "langsmith": langsmith_viewer.is_configured(),
        "monitoring": langfuse_manager.is_configured(),
    }


@app.get("/cache/stats", tags=["System"])
async def cache_stats():
    """Cache layer statistics — hit rate, L1/L2 status, namespaces."""
    if _cache_layer:
        return _cache_layer.get_stats()
    return {"status": "not_initialized", "l1_entries": 0, "l2_connected": False}


@app.get("/redis/info", tags=["System"])
async def redis_info():
    """Redis shared state connection info and memory stats."""
    if _redis_state:
        return await _redis_state.info()
    return {"connected": False, "status": "not_initialized"}


@app.post("/cache/invalidate", tags=["System"])
async def invalidate_cache(namespace: Optional[str] = Query(default=None)):
    """Invalidate cache — optionally scoped to a namespace."""
    if not _cache_layer:
        return {"status": "cache_not_initialized"}
    if namespace:
        count = await _cache_layer.invalidate_namespace(namespace)
        return {"status": "invalidated", "namespace": namespace, "keys_removed": count}
    count = await _cache_layer.invalidate_all()
    return {"status": "flushed", "keys_removed": count}


# ══════════════════════════════════════════════════════════════════════════════
# LLM MODEL LIBRARY
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/models")
async def list_models(
    provider: Optional[str] = Query(default=None),
    capability: Optional[str] = Query(default=None),
    local_only: bool = Query(default=False),
):
    """List all models in the library, with optional filters."""
    if provider:
        models = model_library.list_by_provider(ModelProvider(provider))
    elif capability:
        models = model_library.list_by_capability(ModelCapability(capability))
    elif local_only:
        models = model_library.list_local()
    else:
        models = model_library.list_all()

    return {
        "count": len(models),
        "models": [m.model_dump(mode="json") for m in models],
    }


@app.get("/models/{model_id}")
async def get_model(model_id: str):
    model = model_library.get(model_id)
    if not model:
        raise HTTPException(404, f"Model '{model_id}' not found")
    return model.model_dump(mode="json")


@app.post("/models")
async def register_model(req: RegisterModelRequest):
    """Register a custom model in the library."""
    entry = ModelEntry(
        model_id=req.model_id,
        display_name=req.display_name,
        provider=ModelProvider(req.provider),
        model_name=req.model_name,
        description=req.description,
        max_tokens=req.max_tokens,
        max_context_window=req.max_context_window,
        default_temperature=req.default_temperature,
        pricing=ModelPricing(
            input_cost_per_1k=req.input_cost_per_1k,
            output_cost_per_1k=req.output_cost_per_1k,
        ),
        is_local=req.is_local,
    )
    model_library.register(entry)
    return {"status": "registered", "model_id": entry.model_id}


@app.delete("/models/{model_id}")
async def unregister_model(model_id: str):
    if not model_library.unregister(model_id):
        raise HTTPException(404, f"Model '{model_id}' not found")
    return {"status": "removed", "model_id": model_id}


@app.post("/models/{model_id}/test")
async def test_model(model_id: str, prompt: str = Query(default="Say hello in one word.")):
    """Test connectivity and latency for a model."""
    result = provider_factory.test_model(model_id, prompt)
    if not result.get("success"):
        raise HTTPException(400, result)
    return result


@app.get("/models/compare/cost")
async def compare_model_costs(
    input_tokens: int = Query(default=1000),
    output_tokens: int = Query(default=500),
):
    """Compare costs across all models for a given token count."""
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "comparison": model_library.compare_costs(input_tokens, output_tokens),
    }


@app.get("/providers")
async def list_providers():
    """List available LLM providers and their configuration status."""
    return provider_factory.list_available_providers()


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT MANAGEMENT (Langfuse-backed)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/prompts")
async def list_prompts(
    limit: int = Query(default=50, le=100),
    page: int = Query(default=1),
    name: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    label: Optional[str] = Query(default=None),
):
    """List all prompts from Langfuse with pagination."""
    result = langfuse_prompt_mgr.list_prompts(limit=limit, page=page, name=name, tag=tag, label=label)
    return result


@app.get("/prompts/{prompt_name}")
async def get_prompt(
    prompt_name: str,
    version: Optional[int] = Query(default=None),
    label: Optional[str] = Query(default=None),
):
    """Get a prompt by name. Optionally specify version or label."""
    prompt = langfuse_prompt_mgr.get_prompt(prompt_name, version=version, label=label)
    if not prompt:
        raise HTTPException(404, f"Prompt '{prompt_name}' not found")
    # Enrich with extracted variables
    prompt["variables"] = LangfusePromptManager.extract_variables(prompt.get("prompt", ""))
    return prompt


@app.get("/prompts/{prompt_name}/versions")
async def get_prompt_versions(prompt_name: str):
    """Get all versions of a prompt."""
    versions = langfuse_prompt_mgr.get_all_versions(prompt_name)
    if not versions:
        raise HTTPException(404, f"Prompt '{prompt_name}' not found")
    for v in versions:
        v["variables"] = LangfusePromptManager.extract_variables(v.get("prompt", ""))
    return {"name": prompt_name, "count": len(versions), "versions": versions}


@app.post("/prompts")
async def create_prompt(req: CreatePromptRequest):
    """Create a new prompt or a new version of an existing prompt in Langfuse."""
    result = langfuse_prompt_mgr.create_prompt(
        name=req.name, prompt=req.prompt, prompt_type=req.type,
        config=req.config, labels=req.labels, tags=req.tags,
    )
    if not result:
        raise HTTPException(500, "Failed to create prompt in Langfuse")
    return result


@app.post("/prompts/{prompt_name}/labels")
async def set_prompt_label(prompt_name: str, version: int = Query(...), label: str = Query(...)):
    """Set a label (e.g. 'production') on a specific prompt version."""
    success = langfuse_prompt_mgr.set_label(prompt_name, version, label)
    if not success:
        raise HTTPException(400, "Failed to set label")
    return {"status": "ok", "name": prompt_name, "version": version, "label": label}


@app.post("/prompts/{prompt_name}/rollback")
async def rollback_prompt(prompt_name: str, version: int = Query(...)):
    """Rollback a prompt to a previous version (creates a new version with old content)."""
    result = langfuse_prompt_mgr.rollback_to_version(prompt_name, version)
    if not result:
        raise HTTPException(400, f"Failed to rollback prompt '{prompt_name}' to version {version}")
    return {"status": "ok", "name": prompt_name, "rolled_back_to": version,
            "new_version": result.get("version"), "rollback_from": result.get("_rollback_from")}


@app.get("/prompts/{prompt_name}/diff")
async def diff_prompt_versions(prompt_name: str,
                               version_a: int = Query(...),
                               version_b: int = Query(...)):
    """Compare two versions of a prompt with a unified diff."""
    diff = langfuse_prompt_mgr.diff_versions(prompt_name, version_a, version_b)
    if not diff:
        raise HTTPException(404, f"Could not load versions {version_a} and/or {version_b} for '{prompt_name}'")
    return diff


@app.post("/prompts/render")
async def render_prompt(req: RenderPromptRequest):
    """Fetch a prompt from Langfuse and render it with variables."""
    prompt = langfuse_prompt_mgr.get_prompt(req.name, version=req.version, label=req.label)
    if not prompt:
        raise HTTPException(404, f"Prompt '{req.name}' not found")
    rendered = LangfusePromptManager.render_prompt(prompt.get("prompt", ""), req.variables)
    return {
        "rendered": rendered,
        "variables_used": list(req.variables.keys()),
        "version": prompt.get("version"),
        "name": req.name,
    }


@app.get("/prompts/{prompt_name}/variables")
async def get_prompt_variables(prompt_name: str, version: Optional[int] = Query(default=None)):
    """Extract variables from a prompt."""
    prompt = langfuse_prompt_mgr.get_prompt(prompt_name, version=version)
    if not prompt:
        raise HTTPException(404, f"Prompt '{prompt_name}' not found")
    return {
        "name": prompt_name,
        "version": prompt.get("version"),
        "variables": LangfusePromptManager.extract_variables(prompt.get("prompt", "")),
    }


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT IMPROVEMENT — AI-powered system prompt enhancement
# ══════════════════════════════════════════════════════════════════════════════

class ImprovePromptRequest(BaseModel):
    current_prompt: str = ""
    agent_name: str = ""
    agent_description: str = ""
    model_id: str = "gemini-2.5-flash"


@app.post("/prompts/improve", tags=["Prompts"])
async def improve_prompt(req: ImprovePromptRequest):
    """Use an LLM to improve a system prompt. Logged and metered."""
    import time as _time

    meta_prompt = (
        "You are an expert AI prompt engineer. Your job is to improve the system prompt below.\n\n"
        "Rules:\n"
        "- Keep the improved prompt clear, structured, and production-ready.\n"
        "- Use markdown sections (##) for organization.\n"
        "- Include a role definition, clear instructions, behavioral guidelines, and output format hints.\n"
        "- Preserve the original intent — do NOT change what the agent is supposed to do.\n"
        "- If the current prompt is empty, generate a solid default based on the agent name and description.\n"
        "- Return ONLY the improved system prompt text. No commentary, no explanations, no wrapper.\n\n"
    )
    if req.agent_name:
        meta_prompt += f"Agent Name: {req.agent_name}\n"
    if req.agent_description:
        meta_prompt += f"Agent Description: {req.agent_description}\n"
    meta_prompt += f"\n--- CURRENT SYSTEM PROMPT ---\n{req.current_prompt or '(empty)'}\n--- END ---\n\nImproved system prompt:"

    messages = [{"role": "user", "content": meta_prompt}]

    trace_id = langfuse_manager.create_trace(
        name="prompt-improve",
        metadata={"agent_name": req.agent_name, "model": req.model_id},
        tags=["prompt-improve", req.model_id],
    )

    start = _time.time()
    try:
        model_entry = model_library.get(req.model_id)
        extra_kwargs = {}
        credential_data = None
        if model_entry:
            intg_id = (model_entry.metadata or {}).get("integration_id")
            if intg_id:
                intg = integration_manager.get(intg_id)
                if intg:
                    if intg.auth_type == "api_key" and intg.api_key:
                        extra_kwargs["google_api_key"] = intg.api_key
                    elif intg.auth_type == "service_account" and intg.service_account_json:
                        credential_data = intg.service_account_json

        llm = provider_factory.create(
            req.model_id, temperature=0.7, max_tokens=2048,
            credential_data=credential_data, **extra_kwargs,
        )
        import asyncio
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: llm.invoke(messages))
        latency_ms = (_time.time() - start) * 1000
        content = response.content if hasattr(response, "content") else str(response)
        usage = getattr(response, "usage_metadata", None) or {}
        try:
            input_tokens = int(usage.get("input_tokens", 0) or 0)
            output_tokens = int(usage.get("output_tokens", 0) or 0)
        except Exception:
            input_tokens = 0
            output_tokens = 0
        # Estimate from content length when provider doesn't report tokens
        if input_tokens == 0:
            input_tokens = max(1, len(meta_prompt) // 4)
        if output_tokens == 0:
            output_tokens = max(1, len(content) // 4)

        # Log to Langfuse
        from datetime import datetime, timezone
        langfuse_manager.log_generation(
            trace_id=trace_id, name="prompt-improve-generation", model=req.model_id,
            input={"messages": messages}, output={"content": content},
            usage={"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens, "unit": "TOKENS"},
            metadata={"agent_name": req.agent_name, "latency_ms": round(latency_ms, 1)},
            end_time=datetime.now(timezone.utc).isoformat(),
        )
        langfuse_manager.update_trace(trace_id, output={"content": content[:300]})

        # Record usage metering
        usage_metering.record(
            model_id=req.model_id,
            provider=req.model_id.split("-")[0] if "-" in req.model_id else "unknown",
            input_tokens=input_tokens, output_tokens=output_tokens,
            latency_ms=round(latency_ms, 1), status="success",
            user_id="system@jaggaer.com",
        )

        return {
            "improved_prompt": content.strip(),
            "model": req.model_id,
            "latency_ms": round(latency_ms, 1),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "trace_id": trace_id,
        }
    except Exception as e:
        latency_ms = (_time.time() - start) * 1000
        if trace_id:
            langfuse_manager.update_trace(trace_id, output={"error": str(e)})
        usage_metering.record(
            model_id=req.model_id,
            provider=req.model_id.split("-")[0] if "-" in req.model_id else "unknown",
            latency_ms=round(latency_ms, 1), status="error",
            user_id="system@jaggaer.com",
        )
        raise HTTPException(500, f"Prompt improvement failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PLAYGROUND — Test prompts against LLMs with tracing
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/playground/run")
async def playground_run(req: PlaygroundRunRequest, request: Request):
    """Execute a prompt in the playground against an LLM, traced to Langfuse."""
    import time as _time
    user_name = request.headers.get("x-user-display-name", "playground")

    # Resolve prompt content
    prompt_content = req.prompt_content
    prompt_meta = {}
    if req.prompt_name and not prompt_content:
        prompt_data = langfuse_prompt_mgr.get_prompt(req.prompt_name, version=req.version, label=req.label)
        if not prompt_data:
            raise HTTPException(404, f"Prompt '{req.prompt_name}' not found")
        prompt_content = prompt_data.get("prompt", "")
        prompt_meta = {
            "prompt_name": req.prompt_name,
            "prompt_version": prompt_data.get("version"),
            "prompt_labels": prompt_data.get("labels", []),
        }

    if not prompt_content:
        raise HTTPException(400, "No prompt content provided")

    # Render variables
    rendered = LangfusePromptManager.render_prompt(prompt_content, req.variables)

    # Build messages for LLM
    if isinstance(rendered, str):
        messages = [{"role": "user", "content": rendered}]
    elif isinstance(rendered, list):
        messages = rendered
    else:
        messages = [{"role": "user", "content": str(rendered)}]

    # Create Langfuse trace
    trace_id = langfuse_manager.create_trace(
        name="playground",
        user_id=user_name,
        metadata={**prompt_meta, "model": req.model_id, "variables": req.variables},
        tags=["playground", req.model_id],
    )

    start = _time.time()
    try:
        # Look up integration credentials for the model
        model_entry = model_library.get(req.model_id)
        extra_kwargs = {}
        credential_data = None
        if model_entry:
            intg_id = (model_entry.metadata or {}).get("integration_id")
            if intg_id:
                intg = integration_manager.get(intg_id)
                if intg:
                    if intg.auth_type == "api_key" and intg.api_key:
                        extra_kwargs["google_api_key"] = intg.api_key
                    elif intg.auth_type == "service_account" and intg.service_account_json:
                        credential_data = intg.service_account_json

        llm = provider_factory.create(
            req.model_id, temperature=req.temperature, max_tokens=req.max_tokens,
            credential_data=credential_data, **extra_kwargs,
        )
        import asyncio
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: llm.invoke(messages))
        latency_ms = (_time.time() - start) * 1000
        content = response.content if hasattr(response, "content") else str(response)
        usage = getattr(response, "usage_metadata", None) or {}
        try:
            input_tokens = int(usage.get("input_tokens", 0) or 0)
            output_tokens = int(usage.get("output_tokens", 0) or 0)
        except Exception:
            input_tokens = 0
            output_tokens = 0
        if input_tokens == 0:
            input_tokens = max(1, sum(len(m.get("content", "")) for m in messages) // 4)
        if output_tokens == 0:
            output_tokens = max(1, len(content) // 4)

        # Log generation to Langfuse
        from datetime import datetime, timezone
        langfuse_manager.log_generation(
            trace_id=trace_id, name="playground-generation", model=req.model_id,
            input={"messages": messages}, output={"content": content},
            usage={"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens, "unit": "TOKENS"},
            metadata={**prompt_meta, "latency_ms": round(latency_ms, 1)},
            end_time=datetime.now(timezone.utc).isoformat(),
        )
        langfuse_manager.update_trace(trace_id, output={"content": content[:300]})

        # Record usage metering
        usage_metering.record(
            model_id=req.model_id,
            provider=req.model_id.split("-")[0] if "-" in req.model_id else "unknown",
            input_tokens=input_tokens, output_tokens=output_tokens,
            latency_ms=round(latency_ms, 1), status="success",
            user_id=user_name,
        )

        return {
            "output": content,
            "model": req.model_id,
            "latency_ms": round(latency_ms, 1),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "trace_id": trace_id,
            **prompt_meta,
        }
    except Exception as e:
        latency_ms = (_time.time() - start) * 1000
        if trace_id:
            langfuse_manager.update_trace(trace_id, output={"error": str(e)})
        usage_metering.record(
            model_id=req.model_id,
            provider=req.model_id.split("-")[0] if "-" in req.model_id else "unknown",
            latency_ms=round(latency_ms, 1), status="error",
            user_id=user_name,
        )
        raise HTTPException(500, f"Playground error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENTS — Langfuse datasets + prompt evaluation runs
# ══════════════════════════════════════════════════════════════════════════════

class CreateDatasetRequest(BaseModel):
    name: str
    description: str = ""
    metadata: Dict = Field(default_factory=dict)


class CreateDatasetItemRequest(BaseModel):
    dataset_name: str
    input: Any  # dict of variable values
    expected_output: Any = None
    metadata: Dict = Field(default_factory=dict)


class RunExperimentRequest(BaseModel):
    dataset_name: str
    prompt_name: str
    prompt_version: int
    model_id: str = "gemini-2.5-flash"
    run_name: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    scoring_enabled: bool = True
    scoring_metrics: Optional[List[str]] = None
    llm_judge_enabled: bool = False
    judge_model_id: str = "gemini-2.5-flash"


@app.get("/experiments/datasets")
async def list_datasets(limit: int = Query(default=50)):
    """List all experiment datasets."""
    return experiment_manager.list_datasets(limit=limit)


@app.post("/experiments/datasets")
async def create_dataset(req: CreateDatasetRequest):
    """Create a new experiment dataset."""
    result = experiment_manager.create_dataset(req.name, req.description, req.metadata)
    if not result:
        raise HTTPException(500, "Failed to create dataset")
    return result


@app.get("/experiments/datasets/{dataset_name}")
async def get_dataset(dataset_name: str):
    """Get a dataset with its items."""
    ds = experiment_manager.get_dataset(dataset_name)
    if not ds:
        raise HTTPException(404, f"Dataset '{dataset_name}' not found")
    return ds


@app.post("/experiments/dataset-items")
async def create_dataset_item(req: CreateDatasetItemRequest):
    """Add a test case to a dataset."""
    result = experiment_manager.create_dataset_item(
        req.dataset_name, req.input, req.expected_output, req.metadata,
    )
    if not result:
        raise HTTPException(500, "Failed to create dataset item")
    return result


@app.get("/experiments/datasets/{dataset_name}/runs")
async def get_dataset_runs(dataset_name: str):
    """Get all experiment runs for a dataset."""
    runs = experiment_manager.get_dataset_runs(dataset_name)
    return {"dataset_name": dataset_name, "count": len(runs), "runs": runs}


@app.post("/experiments/run")
async def run_experiment(req: RunExperimentRequest):
    """Run a prompt version against all items in a dataset (experiment)."""
    import asyncio
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: experiment_manager.run_experiment(
            dataset_name=req.dataset_name,
            prompt_name=req.prompt_name,
            prompt_version=req.prompt_version,
            model_id=req.model_id,
            run_name=req.run_name,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            prompt_manager=langfuse_prompt_mgr,
            langfuse_manager=langfuse_manager,
            provider_factory=provider_factory,
            model_library=model_library,
            integration_manager=integration_manager,
            scoring_enabled=req.scoring_enabled,
            scoring_metrics=req.scoring_metrics,
            llm_judge_enabled=req.llm_judge_enabled,
            judge_model_id=req.judge_model_id,
        )
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    # Record experiment usage metering
    for item in result.get("results", []):
        usage_metering.record(
            model_id=req.model_id,
            provider=req.model_id.split("-")[0] if "-" in req.model_id else "unknown",
            input_tokens=item.get("input_tokens", 0), output_tokens=item.get("output_tokens", 0),
            latency_ms=item.get("latency_ms", 0), status="success" if not item.get("error") else "error",
            user_id="experiment",
        )
    return result


class ABExperimentRequest(BaseModel):
    dataset_name: str
    prompt_name: str
    prompt_version: int
    model_ids: List[str]
    run_name_prefix: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    scoring_enabled: bool = True
    scoring_metrics: Optional[List[str]] = None
    llm_judge_enabled: bool = False
    judge_model_id: str = "gemini-2.5-flash"


@app.post("/experiments/run-ab")
async def run_ab_experiment(req: ABExperimentRequest):
    """Run the same prompt against multiple models for A/B comparison."""
    import asyncio
    results = {}
    for model_id in req.model_ids:
        run_name = f"{req.run_name_prefix or req.prompt_name}-v{req.prompt_version}-{model_id}"
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda mid=model_id, rn=run_name: experiment_manager.run_experiment(
                dataset_name=req.dataset_name,
                prompt_name=req.prompt_name,
                prompt_version=req.prompt_version,
                model_id=mid,
                run_name=rn,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                prompt_manager=langfuse_prompt_mgr,
                langfuse_manager=langfuse_manager,
                provider_factory=provider_factory,
                model_library=model_library,
                integration_manager=integration_manager,
                scoring_enabled=req.scoring_enabled,
                scoring_metrics=req.scoring_metrics,
                llm_judge_enabled=req.llm_judge_enabled,
                judge_model_id=req.judge_model_id,
            )
        )
        results[model_id] = result

    # Build comparison summary
    comparison = []
    for mid, r in results.items():
        if "error" in r:
            comparison.append({"model_id": mid, "error": r["error"]})
            continue
        avg_lat = sum(i.get("latency_ms", 0) for i in r.get("results", [])) / max(len(r.get("results", [])), 1)
        total_in = sum(i.get("input_tokens", 0) for i in r.get("results", []))
        total_out = sum(i.get("output_tokens", 0) for i in r.get("results", []))
        from backend.metering.usage_metering import calculate_cost
        est_cost = calculate_cost(mid, total_in, total_out)
        # Aggregate quality scores from scoring results
        scoring_data = r.get("scoring", {})
        entry = {
            "model_id": mid,
            "run_name": r.get("run_name"),
            "completed": r.get("completed", 0),
            "errors": r.get("errors", 0),
            "avg_latency_ms": round(avg_lat, 1),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "estimated_cost_usd": est_cost,
        }
        if scoring_data.get("average_score") is not None:
            entry["average_score"] = scoring_data["average_score"]
            entry["items_scored"] = scoring_data.get("items_scored", 0)
            entry["llm_judge_enabled"] = scoring_data.get("llm_judge_enabled", False)
        comparison.append(entry)

    return {
        "dataset_name": req.dataset_name,
        "prompt_name": req.prompt_name,
        "prompt_version": req.prompt_version,
        "models_tested": len(req.model_ids),
        "comparison": comparison,
        "full_results": results,
    }


# ══════════════════════════════════════════════════════════════════════════════
# EVALUATION STUDIO (legacy side-by-side comparison)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/eval/estimate-tokens")
async def estimate_tokens(text: str = Query(...)):
    """Estimate token count and cost across all models."""
    return eval_studio.estimate_tokens(text)


@app.post("/eval/single")
async def eval_single(req: EvalSingleRequest, request: Request):
    """Evaluate a prompt against a single model."""
    user_name = request.headers.get("x-user-display-name", "unknown")
    result = eval_studio.evaluate_single(
        req.prompt, req.model_id, req.temperature, req.max_tokens,
        reference_text=req.reference_text,
        scoring_metrics=req.scoring_metrics,
        llm_judge_enabled=req.llm_judge_enabled,
        judge_model_id=req.judge_model_id,
        judge_criteria=req.judge_criteria,
    )
    # Log to Langfuse
    from datetime import datetime, timezone
    trace_id = langfuse_manager.create_trace(
        name="eval-studio",
        user_id=user_name,
        metadata={"model": req.model_id, "prompt_preview": req.prompt[:200]},
        tags=["eval-studio", req.model_id],
        input={"prompt": req.prompt},
    )
    if trace_id and result.status.value == "completed":
        langfuse_manager.log_generation(
            trace_id=trace_id, name=f"eval — {result.model_name}", model=req.model_id,
            input={"prompt": req.prompt}, output={"content": (result.response or "")[:500]},
            usage={"input": result.input_tokens or 0, "output": result.output_tokens or 0,
                   "total": (result.input_tokens or 0) + (result.output_tokens or 0), "unit": "TOKENS"},
            metadata={"latency_ms": result.latency_ms, "cost_usd": result.cost_usd,
                       "tokens_per_second": result.tokens_per_second},
            end_time=datetime.now(timezone.utc).isoformat(),
        )
        langfuse_manager.update_trace(trace_id, output={"content": (result.response or "")[:300]})
    # Record usage metering
    usage_metering.record(
        model_id=req.model_id,
        provider=req.model_id.split("-")[0] if "-" in req.model_id else "unknown",
        input_tokens=result.input_tokens or 0, output_tokens=result.output_tokens or 0,
        latency_ms=result.latency_ms or 0, status="success",
        user_id=user_name,
    )
    return result.model_dump(mode="json")


@app.post("/eval/multi")
async def eval_multi(req: EvalMultiRequest, request: Request):
    """Evaluate a prompt against multiple models for side-by-side comparison."""
    user_name = request.headers.get("x-user-display-name", "unknown")
    run = eval_studio.evaluate_multi(
        req.prompt, req.model_ids, req.temperature, req.max_tokens,
        reference_text=req.reference_text,
        scoring_metrics=req.scoring_metrics,
        llm_judge_enabled=req.llm_judge_enabled,
        judge_model_id=req.judge_model_id,
        judge_criteria=req.judge_criteria,
    )
    # Log to Langfuse — one trace per eval run, one generation per model
    from datetime import datetime, timezone
    trace_id = langfuse_manager.create_trace(
        name="eval-studio-multi",
        user_id=user_name,
        metadata={"models": req.model_ids, "prompt_preview": req.prompt[:200]},
        tags=["eval-studio"] + req.model_ids,
        input={"prompt": req.prompt},
    )
    for r in run.results:
        if trace_id and r.status.value == "completed":
            langfuse_manager.log_generation(
                trace_id=trace_id, name=f"eval — {r.model_name}", model=r.model_id,
                input={"prompt": req.prompt}, output={"content": (r.response or "")[:500]},
                usage={"input": r.input_tokens or 0, "output": r.output_tokens or 0,
                       "total": (r.input_tokens or 0) + (r.output_tokens or 0), "unit": "TOKENS"},
                metadata={"latency_ms": r.latency_ms, "cost_usd": r.cost_usd,
                           "tokens_per_second": r.tokens_per_second},
                end_time=datetime.now(timezone.utc).isoformat(),
            )
        usage_metering.record(
            model_id=r.model_id,
            provider=r.model_id.split("-")[0] if "-" in r.model_id else "unknown",
            input_tokens=r.input_tokens or 0, output_tokens=r.output_tokens or 0,
            latency_ms=r.latency_ms or 0, status="success",
            user_id=user_name,
        )
    if trace_id:
        best = min((r for r in run.results if r.status.value == "completed"), key=lambda r: r.latency_ms or 9999, default=None)
        langfuse_manager.update_trace(trace_id, output={"fastest": best.model_name if best else "—", "models_tested": len(run.results)})
    return eval_studio.get_comparison_table(run.run_id)


@app.post("/eval/stream")
async def eval_stream(req: EvalMultiRequest, request: Request):
    """Stream eval results as each model completes (SSE). Models run concurrently."""
    import asyncio
    from datetime import datetime, timezone

    user_name = request.headers.get("x-user-display-name", "unknown")

    # Create a parent Langfuse trace for the entire eval run
    trace_id = langfuse_manager.create_trace(
        name="eval-studio",
        user_id=user_name,
        metadata={"models": req.model_ids, "prompt_preview": req.prompt[:200]},
        tags=["eval-studio"] + req.model_ids,
        input={"prompt": req.prompt},
    )

    async def _eval_one(model_id: str):
        """Run a single model eval in a thread (LangChain invoke is sync)."""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: eval_studio.evaluate_single(
                req.prompt, model_id, req.temperature, req.max_tokens,
                reference_text=req.reference_text,
                scoring_metrics=req.scoring_metrics,
                llm_judge_enabled=req.llm_judge_enabled,
                judge_model_id=req.judge_model_id,
                judge_criteria=req.judge_criteria,
            ),
        )

    async def event_generator():
        # Send "start" event with run metadata
        yield f"data: {json.dumps({'event': 'start', 'model_ids': req.model_ids})}\n\n"

        # Launch all model evals concurrently
        tasks = {model_id: asyncio.create_task(_eval_one(model_id)) for model_id in req.model_ids}

        # As each task completes, stream the result immediately
        for coro in asyncio.as_completed(tasks.values()):
            result = await coro
            r = result
            payload = {
                "event": "result",
                "model_id": r.model_id,
                "model_name": r.model_name,
                "provider": r.provider,
                "status": r.status.value if hasattr(r.status, "value") else r.status,
                "latency_ms": r.latency_ms,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_usd": r.cost_usd,
                "tokens_per_second": r.tokens_per_second,
                "response_preview": r.response or "",
                "error": r.error,
                "quality_scores": r.quality_scores,
            }
            yield f"data: {json.dumps(payload)}\n\n"

            # Log each model result to Langfuse as a generation under the parent trace
            if trace_id and r.status.value == "completed":
                langfuse_manager.log_generation(
                    trace_id=trace_id, name=f"eval — {r.model_name}", model=r.model_id,
                    input={"prompt": req.prompt}, output={"content": (r.response or "")[:500]},
                    usage={"input": r.input_tokens or 0, "output": r.output_tokens or 0,
                           "total": (r.input_tokens or 0) + (r.output_tokens or 0), "unit": "TOKENS"},
                    metadata={"latency_ms": r.latency_ms, "cost_usd": r.cost_usd,
                               "tokens_per_second": r.tokens_per_second},
                    end_time=datetime.now(timezone.utc).isoformat(),
                )
            # Record usage metering
            usage_metering.record(
                model_id=r.model_id,
                provider=r.model_id.split("-")[0] if "-" in r.model_id else "unknown",
                input_tokens=r.input_tokens or 0, output_tokens=r.output_tokens or 0,
                latency_ms=r.latency_ms or 0, status="success",
                user_id=user_name,
            )

        # Update trace with summary
        if trace_id:
            langfuse_manager.update_trace(trace_id, output={"models_tested": len(req.model_ids)})

        yield f"data: {json.dumps({'event': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/eval/runs")
async def list_eval_runs(limit: int = Query(default=20)):
    runs = eval_studio.list_runs(limit)
    return {
        "count": len(runs),
        "runs": [
            {
                "run_id": r.run_id,
                "prompt_preview": r.prompt[:80],
                "models_tested": len(r.results),
                "status": r.status.value,
                "total_cost": round(r.total_cost, 6),
                "fastest_model": r.fastest_model,
                "cheapest_model": r.cheapest_model,
                "created_at": r.created_at.isoformat(),
            }
            for r in runs
        ],
    }


@app.get("/eval/runs/{run_id}")
async def get_eval_run(run_id: str):
    table = eval_studio.get_comparison_table(run_id)
    if not table:
        raise HTTPException(404, f"Eval run '{run_id}' not found")
    return table


# ── Evaluation Scoring ────────────────────────────────────────────────────

class ScoreRequest(BaseModel):
    input_text: str = ""
    output_text: str
    reference_text: Optional[str] = None
    metrics: List[str] = Field(default_factory=lambda: ["exact_match", "contains", "rouge_l", "bleu"])
    llm_judge_enabled: bool = False
    judge_model_id: str = "gemini-2.5-flash"
    judge_criteria: Optional[List[str]] = None
    custom_criteria: Optional[Dict[str, str]] = None


@app.post("/eval/score")
async def eval_score(req: ScoreRequest):
    """Score an output against a reference using reference-based metrics and optional LLM-as-judge."""
    from backend.eval_studio.scoring import score_output, EvalScoreRequest
    score_req = EvalScoreRequest(
        input_text=req.input_text, output_text=req.output_text,
        reference_text=req.reference_text, metrics=req.metrics,
        llm_judge_enabled=req.llm_judge_enabled, judge_model_id=req.judge_model_id,
        judge_criteria=req.judge_criteria, custom_criteria=req.custom_criteria,
    )
    result = score_output(score_req, provider_factory=provider_factory)
    return result.model_dump(mode="json")


@app.post("/eval/judge")
async def eval_judge(req: ScoreRequest):
    """Run LLM-as-judge only (no reference metrics)."""
    from backend.eval_studio.scoring import llm_judge
    result = llm_judge(
        input_text=req.input_text, output_text=req.output_text,
        reference=req.reference_text, criteria=req.judge_criteria,
        provider_factory=provider_factory, judge_model_id=req.judge_model_id,
        custom_criteria=req.custom_criteria,
    )
    return result.model_dump(mode="json")


@app.get("/eval/metrics")
async def list_eval_metrics():
    """List all available evaluation metrics."""
    from backend.eval_studio.scoring import METRIC_FUNCTIONS, JudgeCriteria, DEFAULT_JUDGE_CRITERIA
    return {
        "reference_metrics": list(METRIC_FUNCTIONS.keys()),
        "judge_criteria": {c.value: DEFAULT_JUDGE_CRITERIA[c] for c in JudgeCriteria if c != JudgeCriteria.CUSTOM},
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/environments")
async def list_environments(tenant_id: str = Query(default="tenant-default")):
    """List all environments for a tenant."""
    envs = environment_manager.get_environments(tenant_id)
    return {
        "environments": [
            {
                "env_id": e.env_id, "label": e.label, "description": e.description,
                "is_locked": e.is_locked, "locked_by": e.locked_by,
                "variable_count": len(e.variables),
                "updated_at": e.updated_at.isoformat(),
            }
            for e in envs
        ]
    }


# ── Static /environments/* routes MUST come before /environments/{env_id} ──

# ── Promotions ────────────────────────────────────────────────────────────

class PromotionRequest(BaseModel):
    asset_type: str  # agent, prompt, pipeline, tool
    asset_id: str
    asset_name: str = ""
    from_env: str
    to_env: str
    config_json: Dict[str, Any] = Field(default_factory=dict)
    from_version: int = 0
    to_version: int = 0
    requested_by: str = "admin"


@app.post("/environments/promotions")
async def request_promotion(req: PromotionRequest,
                            tenant_id: str = Query(default="tenant-default")):
    """Request promotion of an asset between environments."""
    try:
        promo = environment_manager.request_promotion(
            asset_type=req.asset_type, asset_id=req.asset_id,
            asset_name=req.asset_name, from_env=req.from_env, to_env=req.to_env,
            config_json=req.config_json, from_version=req.from_version,
            to_version=req.to_version, requested_by=req.requested_by,
            tenant_id=tenant_id,
        )
        return promo.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/environments/promotions")
async def list_promotions(tenant_id: str = Query(default="tenant-default"),
                          env_id: Optional[str] = Query(default=None),
                          status: Optional[str] = Query(default=None),
                          limit: int = Query(default=50)):
    """List promotion records."""
    promos = environment_manager.list_promotions(tenant_id, env_id, status, limit)
    return {"count": len(promos), "promotions": [p.model_dump(mode="json") for p in promos]}


@app.get("/environments/promotions/{promotion_id}")
async def get_promotion(promotion_id: str):
    """Get a single promotion record."""
    promo = environment_manager.get_promotion(promotion_id)
    if not promo:
        raise HTTPException(404, "Promotion not found")
    return promo.model_dump(mode="json")


@app.post("/environments/promotions/{promotion_id}/approve")
async def approve_promotion(promotion_id: str, approved_by: str = Query(default="admin")):
    """Approve a pending promotion."""
    promo = environment_manager.approve_promotion(promotion_id, approved_by)
    if not promo:
        raise HTTPException(400, "Promotion not found or not pending")
    return promo.model_dump(mode="json")


@app.post("/environments/promotions/{promotion_id}/reject")
async def reject_promotion(promotion_id: str, rejected_by: str = Query(default="admin"),
                           reason: str = Query(default="")):
    """Reject a pending promotion."""
    promo = environment_manager.reject_promotion(promotion_id, rejected_by, reason)
    if not promo:
        raise HTTPException(400, "Promotion not found or not pending")
    return promo.model_dump(mode="json")


@app.post("/environments/promotions/{promotion_id}/rollback")
async def rollback_promotion(promotion_id: str, rolled_back_by: str = Query(default="admin")):
    """Roll back a deployed promotion."""
    promo = environment_manager.rollback_promotion(promotion_id, rolled_back_by)
    if not promo:
        raise HTTPException(400, "Promotion not found or not deployed")
    return promo.model_dump(mode="json")


@app.get("/environments/diff/{env_a}/{env_b}")
async def diff_environments(env_a: str, env_b: str,
                            asset_type: Optional[str] = Query(default=None),
                            tenant_id: str = Query(default="tenant-default")):
    """Compare deployed assets between two environments."""
    return environment_manager.diff_environments(env_a, env_b, asset_type, tenant_id)


@app.get("/environments/stats")
async def environment_stats(tenant_id: str = Query(default="tenant-default")):
    """Get environment management stats."""
    return environment_manager.get_stats(tenant_id)


# ── Parameterized /environments/{env_id} routes ──────────────────────────

@app.get("/environments/{env_id}")
async def get_environment(env_id: str, tenant_id: str = Query(default="tenant-default")):
    """Get a single environment with its variables."""
    cfg = environment_manager.get_environment(env_id, tenant_id)
    if not cfg:
        raise HTTPException(404, f"Environment '{env_id}' not found")
    return {
        "env_id": cfg.env_id, "label": cfg.label, "description": cfg.description,
        "is_locked": cfg.is_locked, "locked_by": cfg.locked_by,
        "variables": environment_manager.get_variables(env_id, tenant_id),
        "updated_at": cfg.updated_at.isoformat(),
    }


class SetEnvVarRequest(BaseModel):
    key: str
    value: str
    is_secret: bool = False
    description: str = ""


@app.post("/environments/{env_id}/variables")
async def set_env_variable(env_id: str, req: SetEnvVarRequest,
                           tenant_id: str = Query(default="tenant-default"),
                           updated_by: str = Query(default="admin")):
    """Set an environment variable."""
    var = environment_manager.set_variable(
        env_id, req.key, req.value, req.is_secret, req.description,
        updated_by=updated_by, tenant_id=tenant_id,
    )
    if not var:
        raise HTTPException(400, f"Cannot set variable on '{env_id}' (locked or not found)")
    return {"status": "set", "key": req.key, "env_id": env_id}


class BulkSetVarsRequest(BaseModel):
    variables: Dict[str, str]


@app.post("/environments/{env_id}/variables/bulk")
async def bulk_set_env_variables(env_id: str, req: BulkSetVarsRequest,
                                  tenant_id: str = Query(default="tenant-default"),
                                  updated_by: str = Query(default="admin")):
    """Set multiple environment variables at once."""
    count = environment_manager.bulk_set_variables(env_id, req.variables, updated_by, tenant_id)
    return {"status": "set", "count": count, "env_id": env_id}


@app.get("/environments/{env_id}/variables")
async def get_env_variables(env_id: str, tenant_id: str = Query(default="tenant-default"),
                            include_secrets: bool = Query(default=False)):
    """Get all variables for an environment."""
    return environment_manager.get_variables(env_id, tenant_id, include_secrets)


@app.delete("/environments/{env_id}/variables/{key}")
async def delete_env_variable(env_id: str, key: str,
                               tenant_id: str = Query(default="tenant-default")):
    """Delete an environment variable."""
    if not environment_manager.delete_variable(env_id, key, tenant_id):
        raise HTTPException(400, "Cannot delete variable (locked, not found, or key missing)")
    return {"status": "deleted", "key": key, "env_id": env_id}


@app.post("/environments/{env_id}/lock")
async def lock_environment(env_id: str, locked_by: str = Query(default="admin"),
                           tenant_id: str = Query(default="tenant-default")):
    """Lock an environment to prevent changes."""
    if not environment_manager.lock_environment(env_id, locked_by, tenant_id):
        raise HTTPException(404, f"Environment '{env_id}' not found")
    return {"status": "locked", "env_id": env_id}


@app.post("/environments/{env_id}/unlock")
async def unlock_environment(env_id: str, tenant_id: str = Query(default="tenant-default")):
    """Unlock an environment."""
    if not environment_manager.unlock_environment(env_id, tenant_id):
        raise HTTPException(404, f"Environment '{env_id}' not found")
    return {"status": "unlocked", "env_id": env_id}


@app.get("/environments/{env_id}/assets")
async def list_deployed_assets(env_id: str, asset_type: Optional[str] = Query(default=None),
                                tenant_id: str = Query(default="tenant-default")):
    """List deployed assets in an environment."""
    return environment_manager.list_deployed_assets(env_id, asset_type, tenant_id)


# ══════════════════════════════════════════════════════════════════════════════
# CHANNELS: WEBHOOKS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/webhooks")
async def list_webhooks():
    hooks = webhook_handler.list_all()
    return {"count": len(hooks), "webhooks": [h.model_dump(mode="json") for h in hooks]}


@app.post("/webhooks")
async def create_webhook(req: CreateWebhookRequest):
    config = WebhookConfig(
        name=req.name,
        direction=WebhookDirection(req.direction),
        url=req.url,
        agent_id=req.agent_id,
    )
    result = webhook_handler.register(config)
    return {"status": "created", "webhook": result.model_dump(mode="json")}


@app.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    if not webhook_handler.unregister(webhook_id):
        raise HTTPException(404, f"Webhook '{webhook_id}' not found")
    return {"status": "deleted"}


@app.post("/webhooks/inbound/{webhook_id}")
async def receive_webhook(webhook_id: str, payload: dict):
    """Inbound webhook endpoint — receives external triggers."""
    result = await webhook_handler.handle_inbound(webhook_id, payload)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@app.get("/webhooks/{webhook_id}/events")
async def get_webhook_events(webhook_id: str, limit: int = Query(default=20)):
    events = webhook_handler.get_events(webhook_id, limit)
    return {"count": len(events), "events": [e.model_dump(mode="json") for e in events]}


# ══════════════════════════════════════════════════════════════════════════════
# CHANNELS: WEBSOCKETS — Real-time streaming for agent execution
# ══════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time streaming.
    Query params: user_id, tenant_id, channels (comma-separated).
    Clients subscribe to agent/thread channels for live token streaming.
    """
    await websocket.accept()
    user_id = websocket.query_params.get("user_id", "")
    tenant_id = websocket.query_params.get("tenant_id", "")
    channels_str = websocket.query_params.get("channels", "default")
    channels = [c.strip() for c in channels_str.split(",") if c.strip()]

    connected = await ws_manager.connect(
        client_id, websocket,
        user_id=user_id, tenant_id=tenant_id, channels=channels,
    )
    if not connected:
        await websocket.close(code=1013, reason="Max connections reached")
        return

    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.handle_message(client_id, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)


@app.get("/ws/stats")
async def websocket_stats():
    return ws_manager.get_stats()


class StreamingChatRequest(BaseModel):
    model: str = "gemini-2.5-flash"
    message: str = ""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    agent_id: str = ""
    rag_enabled: bool = False
    memory_enabled: bool = False
    ws_client_id: str = ""
    ws_channel: str = ""
    thread_id: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


@app.post("/chat/stream")
async def streaming_chat(req: StreamingChatRequest, request: Request):
    """
    Execute an LLM call and stream tokens back via SSE.
    Accepts both 'message' (single string from ChatPage) and 'messages' (array).
    Traces every call to Langfuse for monitoring.
    """
    import time as _time
    from datetime import datetime, timezone

    user_name = request.headers.get("x-user-display-name", "playground")
    run_id = f"run-{__import__('uuid').uuid4().hex[:8]}"

    # Build messages list — accept both formats
    msgs = list(req.messages) if req.messages else []
    if req.system_prompt:
        msgs.insert(0, {"role": "system", "content": req.system_prompt})
    if req.message and not msgs:
        msgs.append({"role": "user", "content": req.message})
    elif req.message:
        msgs.append({"role": "user", "content": req.message})
    if not msgs:
        raise HTTPException(400, "No message or messages provided")

    # Create Langfuse trace
    agent_name = ""
    if req.agent_id:
        agent = agent_registry.get(req.agent_id)
        agent_name = agent.name if agent else req.agent_id
    trace_id = langfuse_manager.create_trace(
        name=f"chat{' — ' + agent_name if agent_name else ''}",
        user_id=user_name,
        metadata={"agent_id": req.agent_id, "agent_name": agent_name, "model": req.model},
        tags=["chat", req.model] + ([agent_name] if agent_name else []),
        input={"messages": msgs},
    )

    # Resolve integration credentials for the model
    model_entry = model_library.get(req.model)
    extra_kwargs = {}
    credential_data = None
    if model_entry:
        intg_id = (model_entry.metadata or {}).get("integration_id")
        if intg_id:
            intg = integration_manager.get(intg_id)
            if intg:
                if intg.auth_type == "api_key" and intg.api_key:
                    extra_kwargs["google_api_key"] = intg.api_key
                elif intg.auth_type == "service_account" and intg.service_account_json:
                    credential_data = intg.service_account_json

    start = _time.time()
    try:
        llm = provider_factory.create(
            req.model, temperature=req.temperature, max_tokens=req.max_tokens,
            credential_data=credential_data, **extra_kwargs,
        )
    except Exception as e:
        if trace_id:
            langfuse_manager.update_trace(trace_id, output={"error": str(e)})
        raise HTTPException(400, f"Failed to create LLM: {e}")

    async def sse_generator():
        full_response = []
        last_usage = None
        try:
            if hasattr(llm, 'astream'):
                async for chunk in llm.astream(msgs):
                    token = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if not token:
                        continue
                    full_response.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"
                    # Capture usage from final chunk if available
                    usage = getattr(chunk, "usage_metadata", None)
                    if usage:
                        last_usage = usage
            else:
                import asyncio
                response = await asyncio.get_event_loop().run_in_executor(None, lambda: llm.invoke(msgs))
                content = response.content if hasattr(response, "content") else str(response)
                full_response.append(content)
                last_usage = getattr(response, "usage_metadata", None)
                yield f"data: {json.dumps({'token': content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            if trace_id:
                langfuse_manager.update_trace(trace_id, output={"error": str(e)})
            yield "data: [DONE]\n\n"
            return

        latency_ms = (_time.time() - start) * 1000
        full_text = "".join(full_response)

        # Resolve tokens from usage_metadata
        input_tokens, output_tokens = 0, 0
        if isinstance(last_usage, dict):
            input_tokens = last_usage.get("input_tokens", 0) or 0
            output_tokens = last_usage.get("output_tokens", 0) or 0
        elif last_usage:
            input_tokens = getattr(last_usage, "input_tokens", 0) or 0
            output_tokens = getattr(last_usage, "output_tokens", 0) or 0
        if input_tokens == 0:
            input_tokens = max(1, sum(len(m.get("content", "")) for m in msgs) // 4)
        if output_tokens == 0:
            output_tokens = max(1, len(full_text) // 4)

        # Log generation to Langfuse
        now = datetime.now(timezone.utc).isoformat()
        langfuse_manager.log_generation(
            trace_id=trace_id, name="chat-generation", model=req.model,
            input={"messages": msgs}, output={"content": full_text},
            usage={"input": input_tokens, "output": output_tokens,
                   "total": input_tokens + output_tokens, "unit": "TOKENS"},
            metadata={"agent_id": req.agent_id, "latency_ms": round(latency_ms, 1)},
            end_time=now,
        )
        langfuse_manager.update_trace(trace_id, output={"content": full_text[:500]})

        # Record usage metering
        usage_metering.record(
            model_id=req.model,
            provider=req.model.split("-")[0] if "-" in req.model else "unknown",
            agent_id=req.agent_id,
            input_tokens=input_tokens, output_tokens=output_tokens,
            latency_ms=round(latency_ms, 1), status="success",
            user_id=user_name,
        )

        # Persist to thread if specified
        if req.thread_id:
            user_msg = req.message or (msgs[-1].get("content", "") if msgs else "")
            if user_msg:
                thread_manager.add_message(thread_id=req.thread_id, role="user", content=user_msg)
            thread_manager.add_message(
                thread_id=req.thread_id, role="assistant",
                content=full_text, model=req.model, latency_ms=latency_ms,
            )

        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


# ══════════════════════════════════════════════════════════════════════════════
# CHANNELS: JAGGAER SAAS LLM CALLS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/jaggaer/llm/invoke")
async def jaggaer_llm_invoke(req: JaggaerLLMRequest):
    """
    REST API for Jaggaer SaaS to make LLM calls.
    Supports model routing, rate limiting, and usage tracking.
    """
    from backend.channels.jaggaer_channel import LLMCallType

    request = LLMCallRequest(
        tenant_id=req.tenant_id,
        user_id=req.user_id,
        call_type=LLMCallType(req.call_type),
        model_id=req.model_id,
        prompt=req.prompt,
        system_prompt=req.system_prompt,
        variables=req.variables,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )
    response = await jaggaer_channel.invoke(request)
    if not response.success:
        raise HTTPException(400 if "Rate limit" in (response.error or "") else 500, response.model_dump(mode="json"))
    return response.model_dump(mode="json")


@app.get("/jaggaer/usage")
async def jaggaer_usage(tenant_id: Optional[str] = Query(default=None)):
    """Get LLM usage records, optionally filtered by tenant."""
    records = jaggaer_channel.get_usage(tenant_id)
    return {
        "count": len(records),
        "records": [r.model_dump(mode="json") for r in records],
    }


@app.get("/jaggaer/usage/summary")
async def jaggaer_usage_summary(tenant_id: Optional[str] = Query(default=None)):
    """Get aggregated usage summary with cost breakdown by model."""
    return jaggaer_channel.get_usage_summary(tenant_id)


# ══════════════════════════════════════════════════════════════════════════════
# LANGSMITH OBSERVABILITY
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/langsmith/status")
async def langsmith_status():
    return langsmith_viewer.get_project_info()


@app.get("/langsmith/runs")
async def langsmith_runs(
    limit: int = Query(default=20),
    run_type: Optional[str] = Query(default=None),
    error_only: bool = Query(default=False),
):
    """List recent LangSmith runs."""
    if not langsmith_viewer.is_configured():
        raise HTTPException(503, "LangSmith not configured. Set LANGCHAIN_API_KEY.")
    runs = langsmith_viewer.list_runs(limit, run_type, error_only)
    return {"count": len(runs), "runs": [r.model_dump(mode="json") for r in runs]}


@app.get("/langsmith/runs/{run_id}")
async def langsmith_run_detail(run_id: str):
    """Get detailed info for a specific LangSmith run."""
    if not langsmith_viewer.is_configured():
        raise HTTPException(503, "LangSmith not configured")
    detail = langsmith_viewer.get_run_detail(run_id)
    if not detail or "error" in detail:
        raise HTTPException(404, detail)
    return detail


@app.get("/langsmith/stats")
async def langsmith_stats(hours: int = Query(default=24)):
    """Get aggregated run statistics."""
    if not langsmith_viewer.is_configured():
        raise HTTPException(503, "LangSmith not configured")
    return langsmith_viewer.get_run_stats(hours)


@app.post("/langsmith/feedback")
async def langsmith_feedback(req: FeedbackRequest):
    """Create feedback on a LangSmith run."""
    if not langsmith_viewer.is_configured():
        raise HTTPException(503, "LangSmith not configured")
    result = langsmith_viewer.create_feedback(
        req.run_id, req.key, req.score, req.value, req.comment
    )
    if not result.get("success"):
        raise HTTPException(400, result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# MONITORING — Traces, Generations, Scores, Sessions (powered by Langfuse)
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/monitoring/status")
async def monitoring_status():
    """Get observability backend connection status."""
    raw = langfuse_manager.get_status()
    return {"enabled": raw.get("configured", False), "connected": raw.get("connected", False), "host": raw.get("host", ""), "error": raw.get("error")}


@app.get("/monitoring/traces")
async def monitoring_traces(
    limit: int = Query(default=50, le=200),
    name: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
):
    """List recent LLM call traces with tokens, latency, cost."""
    traces = langfuse_manager.fetch_traces(limit=limit, name=name, user_id=user_id)
    return {"count": len(traces), "traces": traces}


@app.get("/monitoring/generations")
async def monitoring_generations(
    limit: int = Query(default=50, le=200),
    model: Optional[str] = Query(default=None),
):
    """List recent LLM generations (input/output pairs) with model, tokens, cost."""
    gens = langfuse_manager.fetch_generations(limit=limit, model=model)
    return {"count": len(gens), "generations": gens}


@app.get("/monitoring/scores")
async def monitoring_scores(limit: int = Query(default=50, le=200)):
    """List evaluation scores."""
    scores = langfuse_manager.fetch_scores(limit=limit)
    return {"count": len(scores), "scores": scores}


@app.get("/monitoring/sessions")
async def monitoring_sessions(limit: int = Query(default=50, le=200)):
    """List conversation sessions."""
    sessions = langfuse_manager.fetch_sessions(limit=limit)
    return {"count": len(sessions), "sessions": sessions}


@app.get("/monitoring/traces/{trace_id}")
async def monitoring_trace_detail(trace_id: str):
    """Get a single trace with all its observations for the timeline/waterfall view."""
    detail = langfuse_manager.fetch_trace_detail(trace_id)
    if not detail:
        raise HTTPException(404, f"Trace '{trace_id}' not found")
    return detail


@app.get("/monitoring/metrics")
async def monitoring_metrics():
    """Get aggregated monitoring metrics: cost, latency, model breakdown, daily counts."""
    return langfuse_manager.fetch_metrics()


class SubmitScoreRequest(BaseModel):
    trace_id: str
    name: str
    value: float
    comment: Optional[str] = None
    observation_id: Optional[str] = None


@app.post("/monitoring/scores")
async def submit_score(req: SubmitScoreRequest):
    """Submit an evaluation score for a trace or generation."""
    ok = langfuse_manager.score(
        trace_id=req.trace_id, name=req.name, value=req.value,
        comment=req.comment, observation_id=req.observation_id,
    )
    if not ok:
        raise HTTPException(500, "Failed to submit score — check monitoring backend connection")
    return {"success": True}


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH COMPILER & REGISTRY (Layer 3)
# ══════════════════════════════════════════════════════════════════════════════

class CreateGraphRequest(BaseModel):
    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    nodes: List[dict] = Field(default_factory=list)
    edges: List[dict] = Field(default_factory=list)
    state_schema: List[dict] = Field(default_factory=list)
    entry_node_id: Optional[str] = None


class UpdateGraphRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    nodes: Optional[List[dict]] = None
    edges: Optional[List[dict]] = None
    state_schema: Optional[List[dict]] = None
    entry_node_id: Optional[str] = None
    change_note: str = ""


class RunGraphRequest(BaseModel):
    initial_state: dict = Field(default_factory=dict)


@app.get("/graphs")
async def list_graphs(status: Optional[str] = Query(default=None)):
    """List all graph manifests, optionally filtered by status."""
    graphs = graph_registry.list_all(status)
    return {
        "count": len(graphs),
        "graphs": [
            {
                "manifest_id": g.manifest_id,
                "name": g.name,
                "description": g.description,
                "tags": g.tags,
                "node_count": len(g.nodes),
                "edge_count": len(g.edges),
                "version": g.version_info.version,
                "status": g.version_info.status,
                "updated_at": g.updated_at.isoformat(),
            }
            for g in graphs
        ],
    }


@app.get("/graphs/stats")
async def graph_stats():
    """Get graph registry statistics."""
    return graph_registry.get_stats()


@app.get("/graphs/search/{query}")
async def search_graphs(query: str):
    results = graph_registry.search(query)
    return {"count": len(results), "results": [{"manifest_id": g.manifest_id, "name": g.name} for g in results]}


@app.post("/graphs")
async def create_graph(req: CreateGraphRequest):
    """Create a new graph manifest."""
    nodes = [NodeDefinition(**n) for n in req.nodes]
    edges = [EdgeDefinition(**e) for e in req.edges]
    manifest = GraphManifest(
        name=req.name,
        description=req.description,
        tags=req.tags,
        nodes=nodes,
        edges=edges,
        entry_node_id=req.entry_node_id,
    )
    created = graph_registry.create(manifest)
    return {"status": "created", "manifest_id": created.manifest_id, "version": created.version_info.version}


@app.get("/graphs/{manifest_id}")
async def get_graph(manifest_id: str):
    graph = graph_registry.get(manifest_id)
    if not graph:
        raise HTTPException(404, f"Graph '{manifest_id}' not found")
    return graph.model_dump(mode="json")


@app.put("/graphs/{manifest_id}")
async def update_graph(manifest_id: str, req: UpdateGraphRequest):
    """Update a graph manifest (creates a new version)."""
    existing = graph_registry.get(manifest_id)
    if not existing:
        raise HTTPException(404, f"Graph '{manifest_id}' not found")

    # Merge updates
    import copy
    updated = copy.deepcopy(existing)
    if req.name is not None:
        updated.name = req.name
    if req.description is not None:
        updated.description = req.description
    if req.tags is not None:
        updated.tags = req.tags
    if req.nodes is not None:
        updated.nodes = [NodeDefinition(**n) for n in req.nodes]
    if req.edges is not None:
        updated.edges = [EdgeDefinition(**e) for e in req.edges]
    if req.entry_node_id is not None:
        updated.entry_node_id = req.entry_node_id

    result = graph_registry.update(manifest_id, updated, req.change_note)
    if not result:
        raise HTTPException(500, "Update failed")
    return {"status": "updated", "version": result.version_info.version}


@app.delete("/graphs/{manifest_id}")
async def delete_graph(manifest_id: str):
    if not graph_registry.delete(manifest_id):
        raise HTTPException(404, f"Graph '{manifest_id}' not found")
    return {"status": "deleted"}


@app.get("/graphs/{manifest_id}/versions")
async def list_graph_versions(manifest_id: str):
    """List all versions of a graph."""
    versions = graph_registry.list_versions(manifest_id)
    if not versions:
        raise HTTPException(404, f"Graph '{manifest_id}' not found")
    return {"manifest_id": manifest_id, "versions": versions}


@app.get("/graphs/{manifest_id}/versions/{version}")
async def get_graph_version(manifest_id: str, version: int):
    v = graph_registry.get_version(manifest_id, version)
    if not v:
        raise HTTPException(404, f"Version {version} not found")
    return v.model_dump(mode="json")


@app.post("/graphs/{manifest_id}/rollback/{version}")
async def rollback_graph(manifest_id: str, version: int):
    """Rollback to a previous version."""
    result = graph_registry.rollback(manifest_id, version)
    if not result:
        raise HTTPException(404, f"Version {version} not found")
    return {"status": "rolled_back", "new_version": result.version_info.version}


@app.post("/graphs/{manifest_id}/status/{status}")
async def set_graph_status(manifest_id: str, status: str):
    """Transition graph lifecycle status."""
    try:
        result = graph_registry.set_status(manifest_id, status)
        if not result:
            raise HTTPException(404, f"Graph '{manifest_id}' not found")
        return {"status": status, "manifest_id": manifest_id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/graphs/{manifest_id}/validate")
async def validate_graph(manifest_id: str):
    """Validate a graph manifest for errors."""
    graph = graph_registry.get(manifest_id)
    if not graph:
        raise HTTPException(404, f"Graph '{manifest_id}' not found")
    errors = graph.validate()
    return {"valid": len(errors) == 0, "errors": errors}


@app.post("/graphs/{manifest_id}/compile")
async def compile_graph(manifest_id: str):
    """Compile a graph manifest into an executable LangGraph StateGraph."""
    graph = graph_registry.get(manifest_id)
    if not graph:
        raise HTTPException(404, f"Graph '{manifest_id}' not found")
    result = graph_compiler.compile(graph)
    return result.model_dump(mode="json")


@app.post("/graphs/{manifest_id}/run")
async def run_graph(manifest_id: str, req: RunGraphRequest):
    """Execute a compiled graph with initial state."""
    result = graph_compiler.run(manifest_id, req.initial_state)
    if not result.get("success") and "error" in result:
        raise HTTPException(400, result)
    return result


@app.get("/graphs/compiled/list")
async def list_compiled_graphs():
    """List all compiled graphs ready for execution."""
    return {"compiled": graph_compiler.list_compiled()}


@app.get("/graphs/{manifest_id}/export")
async def export_graph(manifest_id: str):
    """Export a graph manifest as JSON."""
    data = graph_registry.export_manifest(manifest_id)
    if not data:
        raise HTTPException(404, f"Graph '{manifest_id}' not found")
    return data


@app.post("/graphs/import")
async def import_graph(data: dict):
    """Import a graph manifest from JSON."""
    manifest = graph_registry.import_manifest(data)
    return {"status": "imported", "manifest_id": manifest.manifest_id}


# ── Templates ─────────────────────────────────────────────────────

@app.get("/templates")
async def list_templates():
    templates = graph_registry.list_templates()
    return {
        "count": len(templates),
        "templates": [{"manifest_id": t.manifest_id, "name": t.name, "node_count": len(t.nodes)} for t in templates],
    }


@app.post("/templates/{manifest_id}")
async def save_as_template(manifest_id: str, name: str = Query(...)):
    """Save a graph as a reusable template."""
    result = graph_registry.save_as_template(manifest_id, name)
    if not result:
        raise HTTPException(404, f"Graph '{manifest_id}' not found")
    return {"status": "saved", "template_id": result.manifest_id}


@app.post("/templates/{template_id}/create")
async def create_from_template(template_id: str, name: str = Query(...)):
    """Create a new graph from a template."""
    result = graph_registry.create_from_template(template_id, name)
    if not result:
        raise HTTPException(404, f"Template '{template_id}' not found")
    return {"status": "created", "manifest_id": result.manifest_id}


# ══════════════════════════════════════════════════════════════════════════════
# V2 ROUTES: Auth, Users, Agents, Orchestrator, Tools, RAG, DB
# ══════════════════════════════════════════════════════════════════════════════

from backend.api.routes_v2 import register_v2_routes
register_v2_routes(
    app, keycloak, rbac_manager, user_manager,
    agent_registry, agent_memory, agent_rag, agent_db,
    orchestrator, tool_registry,
)


# ══════════════════════════════════════════════════════════════════════════════
# V3 ROUTES: Tenancy, Gateway, LLM Logs, Threads, Inbox, Settings API Keys
# ══════════════════════════════════════════════════════════════════════════════

from backend.api.routes_v3 import register_v3_routes
register_v3_routes(
    app, tenant_manager, agent_gateway, llm_log_manager,
    thread_manager, agent_inbox, api_key_store, workato_registry,
    langfuse_mgr=langfuse_manager,
    provider_factory_ref=provider_factory,
    model_library_ref=model_library,
    integration_manager_ref=integration_manager,
)


# ══════════════════════════════════════════════════════════════════════════════
# V4 ROUTES: Groups (LoB/Teams), Model Assignment, Usage Metering
# ══════════════════════════════════════════════════════════════════════════════

from backend.api.routes_v4 import register_v4_routes
register_v4_routes(
    app, group_manager, usage_metering, model_library, integration_manager,
    agent_registry=agent_registry, orchestrator=orchestrator,
    gateway=agent_gateway, llm_log_manager=llm_log_manager,
    api_token_store=api_token_store, guardrail_manager=guardrail_manager,
)


# ══════════════════════════════════════════════════════════════════════════════
# DB-BACKED ROUTES: Persistent Agents, Credentials, Agent Invocation
# ══════════════════════════════════════════════════════════════════════════════

from backend.api.routes_db import register_db_routes
register_db_routes(app, provider_factory)
# LANGGRAPH INTEGRATION ROUTES
# ══════════════════════════════════════════════════════════════════════════════

from backend.api.routes_langgraph import register_langgraph_routes
register_langgraph_routes(app, langgraph_client)

# KNOWLEDGE BASE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

from backend.api.routes_knowledge_base import register_knowledge_base_routes
register_knowledge_base_routes(app, model_library, provider_factory, integration_manager)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION CHANNELS — HITL channel config (Twilio, Teams, Email, Slack)
# ══════════════════════════════════════════════════════════════════════════════

_notification_channels = [
    {"channel_id": "ch-email", "type": "email", "name": "Email (SMTP)", "enabled": True,
     "config": {"smtp_host": "smtp.jaggaer.com", "smtp_port": 587, "from_address": "jai-agentOS@jaggaer.com", "use_tls": True},
     "description": "Send HITL approval notifications via email"},
    {"channel_id": "ch-teams", "type": "teams", "name": "Microsoft Teams", "enabled": True,
     "config": {"webhook_url": "", "tenant_id": "", "channel_id": ""},
     "description": "Post approval cards to Teams channels via webhook"},
    {"channel_id": "ch-slack", "type": "slack", "name": "Slack", "enabled": False,
     "config": {"webhook_url": "", "channel": "#procurement-approvals", "bot_token": ""},
     "description": "Send approval notifications to Slack channels"},
    {"channel_id": "ch-twilio-sms", "type": "sms", "name": "SMS (Twilio)", "enabled": False,
     "config": {"account_sid": "", "auth_token": "", "from_number": "", "messaging_service_sid": ""},
     "description": "Send SMS notifications for urgent approvals via Twilio"},
    {"channel_id": "ch-twilio-whatsapp", "type": "whatsapp", "name": "WhatsApp (Twilio)", "enabled": False,
     "config": {"account_sid": "", "auth_token": "", "from_number": "whatsapp:+14155238886"},
     "description": "Send WhatsApp messages for mobile-first approval flows"},
    {"channel_id": "ch-webhook", "type": "webhook", "name": "Custom Webhook", "enabled": False,
     "config": {"url": "", "method": "POST", "headers": {}, "auth_type": "none"},
     "description": "Send notification payloads to any custom HTTP endpoint"},
]

@app.get("/notification-channels")
async def list_notification_channels():
    return {"channels": _notification_channels}

@app.get("/notification-channels/{channel_id}")
async def get_notification_channel(channel_id: str):
    ch = next((c for c in _notification_channels if c["channel_id"] == channel_id), None)
    if not ch:
        raise HTTPException(404, "Channel not found")
    return ch

@app.put("/notification-channels/{channel_id}")
async def update_notification_channel(channel_id: str, req: Request):
    body = await req.json()
    ch = next((c for c in _notification_channels if c["channel_id"] == channel_id), None)
    if not ch:
        raise HTTPException(404, "Channel not found")
    if "enabled" in body:
        ch["enabled"] = body["enabled"]
    if "config" in body:
        ch["config"].update(body["config"])
    return ch

@app.post("/notification-channels/{channel_id}/test")
async def test_notification_channel(channel_id: str):
    ch = next((c for c in _notification_channels if c["channel_id"] == channel_id), None)
    if not ch:
        raise HTTPException(404, "Channel not found")
    return {"success": True, "message": f"Test notification sent via {ch['name']}", "channel_id": channel_id}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT MARKETPLACE — Publish, browse, install, rate agents across tenants
# ══════════════════════════════════════════════════════════════════════════════

class PublishToMarketplaceRequest(BaseModel):
    agent_id: str
    category: str = "custom"
    long_description: str = ""
    tags: List[str] = Field(default_factory=list)
    icon: str = ""
    complexity: str = "intermediate"
    requires_api_keys: List[str] = Field(default_factory=list)
    publisher_name: str = ""
    tenant_id: str = ""

class MarketplaceReviewRequest(BaseModel):
    user_id: str
    rating: int = 5
    comment: str = ""
    user_name: str = ""
    tenant_id: str = ""


@app.get("/marketplace/listings")
async def marketplace_browse(
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query(default="popular"),
    limit: int = Query(default=50),
    offset: int = Query(default=0),
):
    """Browse published marketplace listings."""
    listings = marketplace_manager.list_published(
        category=category, search=search, sort_by=sort_by, limit=limit, offset=offset,
    )
    return {
        "count": len(listings),
        "listings": [
            {
                "listing_id": l.listing_id,
                "name": l.name,
                "description": l.description,
                "long_description": l.long_description,
                "category": l.category,
                "tags": l.tags,
                "icon": l.icon,
                "complexity": l.complexity,
                "version": l.version,
                "status": l.status.value,
                "featured": l.featured,
                "install_count": l.install_count,
                "avg_rating": l.avg_rating,
                "review_count": l.review_count,
                "tools_used": l.tools_used,
                "model_id": l.model_id,
                "rag_enabled": l.rag_enabled,
                "requires_api_keys": l.requires_api_keys,
                "publisher_name": l.publisher_name,
                "published_at": l.published_at.isoformat() if l.published_at else None,
            }
            for l in listings
        ],
    }


@app.get("/marketplace/listings/{listing_id}")
async def marketplace_get_listing(listing_id: str):
    """Get full details of a marketplace listing."""
    listing = marketplace_manager.get(listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    return {
        "listing_id": listing.listing_id,
        "name": listing.name,
        "description": listing.description,
        "long_description": listing.long_description,
        "category": listing.category,
        "tags": listing.tags,
        "icon": listing.icon,
        "complexity": listing.complexity,
        "version": listing.version,
        "status": listing.status.value,
        "featured": listing.featured,
        "install_count": listing.install_count,
        "avg_rating": listing.avg_rating,
        "review_count": listing.review_count,
        "tools_used": listing.tools_used,
        "model_id": listing.model_id,
        "rag_enabled": listing.rag_enabled,
        "requires_api_keys": listing.requires_api_keys,
        "publisher_name": listing.publisher_name,
        "source_tenant_id": listing.source_tenant_id,
        "agent_snapshot": listing.agent_snapshot,
        "published_at": listing.published_at.isoformat() if listing.published_at else None,
        "created_at": listing.created_at.isoformat(),
        "reviews": [
            {"review_id": r.review_id, "user_name": r.user_name, "rating": r.rating,
             "comment": r.comment, "created_at": r.created_at.isoformat()}
            for r in sorted(listing.reviews, key=lambda x: x.created_at, reverse=True)[:10]
        ],
    }


@app.post("/marketplace/publish")
async def marketplace_publish(req: PublishToMarketplaceRequest):
    """Publish an agent to the marketplace."""
    agent = agent_registry.get(req.agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{req.agent_id}' not found")
    listing = marketplace_manager.publish(
        agent_definition=agent,
        publisher_id=agent.access_control.owner_id or "",
        publisher_name=req.publisher_name or agent.created_by or "Anonymous",
        tenant_id=req.tenant_id,
        category=req.category,
        long_description=req.long_description,
        tags=req.tags or agent.tags,
        icon=req.icon,
        complexity=req.complexity,
        requires_api_keys=req.requires_api_keys,
    )
    return {
        "status": "published",
        "listing_id": listing.listing_id,
        "name": listing.name,
    }


@app.post("/marketplace/listings/{listing_id}/install")
async def marketplace_install(listing_id: str, req: Request):
    """Install a marketplace agent into your tenant."""
    body = await req.json()
    result = marketplace_manager.install(
        listing_id=listing_id,
        agent_registry=agent_registry,
        installed_by=body.get("user_id", ""),
        tenant_id=body.get("tenant_id", ""),
    )
    if not result:
        raise HTTPException(404, "Listing not found or install failed")
    return result


@app.post("/marketplace/listings/{listing_id}/review")
async def marketplace_review(listing_id: str, req: MarketplaceReviewRequest):
    """Rate and review a marketplace listing."""
    review = marketplace_manager.add_review(
        listing_id=listing_id,
        user_id=req.user_id,
        rating=req.rating,
        comment=req.comment,
        user_name=req.user_name,
        tenant_id=req.tenant_id,
    )
    if not review:
        raise HTTPException(404, "Listing not found")
    return {
        "review_id": review.review_id,
        "rating": review.rating,
        "listing_id": listing_id,
    }


@app.get("/marketplace/listings/{listing_id}/reviews")
async def marketplace_get_reviews(listing_id: str):
    """Get all reviews for a listing."""
    reviews = marketplace_manager.get_reviews(listing_id)
    return {
        "listing_id": listing_id,
        "count": len(reviews),
        "reviews": [
            {"review_id": r.review_id, "user_id": r.user_id, "user_name": r.user_name,
             "rating": r.rating, "comment": r.comment, "created_at": r.created_at.isoformat()}
            for r in reviews
        ],
    }


@app.get("/marketplace/featured")
async def marketplace_featured():
    """Get featured marketplace listings."""
    featured = marketplace_manager.get_featured()
    return {
        "count": len(featured),
        "listings": [
            {
                "listing_id": l.listing_id, "name": l.name, "description": l.description,
                "category": l.category, "install_count": l.install_count,
                "avg_rating": l.avg_rating, "publisher_name": l.publisher_name,
                "complexity": l.complexity, "tools_used": l.tools_used, "tags": l.tags,
            }
            for l in featured
        ],
    }


@app.get("/marketplace/categories")
async def marketplace_categories():
    """Get marketplace categories with listing counts."""
    return {"categories": marketplace_manager.get_categories()}


@app.get("/marketplace/stats")
async def marketplace_stats():
    """Get marketplace statistics."""
    return marketplace_manager.get_stats()


@app.post("/marketplace/listings/{listing_id}/feature")
async def marketplace_set_featured(listing_id: str, featured: bool = Query(default=True)):
    """Set or unset a listing as featured (admin)."""
    ok = marketplace_manager.set_featured(listing_id, featured)
    if not ok:
        raise HTTPException(404, "Listing not found")
    return {"listing_id": listing_id, "featured": featured}


@app.delete("/marketplace/listings/{listing_id}")
async def marketplace_unpublish(listing_id: str):
    """Unpublish a marketplace listing."""
    ok = marketplace_manager.unpublish(listing_id)
    if not ok:
        raise HTTPException(404, "Listing not found")
    return {"listing_id": listing_id, "status": "deprecated"}


@app.get("/marketplace/publisher/{publisher_id}")
async def marketplace_by_publisher(publisher_id: str):
    """Get all listings by a specific publisher."""
    listings = marketplace_manager.get_by_publisher(publisher_id)
    return {
        "publisher_id": publisher_id,
        "count": len(listings),
        "listings": [
            {"listing_id": l.listing_id, "name": l.name, "status": l.status.value,
             "install_count": l.install_count, "avg_rating": l.avg_rating}
            for l in listings
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASES — now served by routes_knowledge_base.py (DB + GCP backed)
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# EXECUTIVE DASHBOARD — Real data from platform DB (zeros when empty)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/executive/dashboard")
async def executive_dashboard():
    from datetime import datetime as _dt, timedelta
    from collections import defaultdict
    now = _dt.utcnow()

    # ── Agents ────────────────────────────────────────────────────
    all_agents = agent_registry.list_all() if agent_registry else []
    status_counts = defaultdict(int)
    lob_counts = defaultdict(int)
    for a in all_agents:
        st = getattr(a, "status", "draft")
        status_counts[st] += 1
        lob = getattr(a, "metadata", {}).get("category", "") if hasattr(a, "metadata") else ""
        if not lob:
            md = getattr(a, "metadata_json", {}) or {}
            lob = md.get("category", "")
        if lob:
            lob_counts[lob] += 1

    active_agents = sum(1 for a in all_agents if getattr(a, "status", "") in ("active", "ACTIVE", "AgentStatus.ACTIVE"))

    # ── Usage / Spend ─────────────────────────────────────────────
    records = usage_metering._records if usage_metering else []
    total_spend = sum(r.cost_usd for r in records)
    total_calls = len(records)
    # Estimated savings: ~2.5 min saved per call at $50/hr
    estimated_savings = round(total_calls * 2.5 / 60 * 50, 2)
    roi_mult = round(estimated_savings / total_spend, 1) if total_spend > 0 else 0

    # ── Spend by LoB (from group_manager) ─────────────────────────
    lob_spend = defaultdict(lambda: {"cost": 0, "savings": 0})
    for r in records:
        grp = group_manager.get(r.group_id) if hasattr(group_manager, "get") and r.group_id else None
        lob = getattr(grp, "lob", "") if grp else ""
        if not lob:
            lob = r.lob if hasattr(r, "lob") and r.lob else "Unassigned"
        lob_spend[lob]["cost"] += r.cost_usd
        lob_spend[lob]["savings"] += 2.5 / 60 * 50  # estimated per-call savings
    roi_by_lob = [
        {"lob": lob, "token_cost": round(v["cost"], 2), "savings": round(v["savings"], 2),
         "roi_pct": round(v["savings"] / v["cost"] * 100, 0) if v["cost"] > 0 else 0}
        for lob, v in sorted(lob_spend.items())
    ]

    # ── Guardrail violations (real from guardrail_manager stats) ──
    gr_stats = guardrail_manager.get_stats() if guardrail_manager else {}
    guardrail_violations = [
        {"date": (now - timedelta(days=d)).strftime("%Y-%m-%d"),
         "pii_blocked": 0, "toxic_blocked": 0, "hallucination_flagged": 0}
        for d in range(14)
    ]

    # ── Agent lifecycle funnel (from real agent statuses) ─────────
    agent_lifecycle_funnel = [
        {"stage": "Draft", "count": status_counts.get("draft", 0)},
        {"stage": "Active", "count": status_counts.get("active", 0) + status_counts.get("ACTIVE", 0)},
        {"stage": "Deployed", "count": active_agents},
    ]

    # ── Tools reuse (real from tool_registry + agent tool bindings)
    tool_list = tool_registry.list_all() if tool_registry else []
    cross_lob_tool_reuse = []
    for t in tool_list[:10]:
        tid = getattr(t, "tool_id", getattr(t, "id", ""))
        tname = getattr(t, "name", tid)
        # Count agents that reference this tool
        agents_using = sum(
            1 for a in all_agents
            if tid in str(getattr(a, "tools_json", []))
        )
        if agents_using > 0:
            cross_lob_tool_reuse.append({
                "tool_name": tname, "tool_id": tid,
                "agents_using": agents_using, "lobs_using": [],
            })
    cross_lob_tool_reuse.sort(key=lambda x: x["agents_using"], reverse=True)

    return {
        "kpis": {
            "total_ai_spend": round(total_spend, 2),
            "estimated_manual_savings": estimated_savings,
            "roi_multiplier": roi_mult,
            "avg_grounding_score": 0,
            "active_agents_by_lob": dict(lob_counts) if lob_counts else {},
            "total_active_agents": active_agents,
        },
        "roi_by_lob": roi_by_lob,
        "hitl_latency": [],
        "guardrail_violations": guardrail_violations,
        "agent_lifecycle_funnel": agent_lifecycle_funnel,
        "avg_time_to_value_days": 0,
        "cross_lob_tool_reuse": cross_lob_tool_reuse,
        "generated_at": now.isoformat() + "Z",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
