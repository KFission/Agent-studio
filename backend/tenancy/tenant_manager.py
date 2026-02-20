"""
JAI Agent OS — Multi-Tenancy Manager
Provides tenant isolation, per-tenant quotas, and tenant-scoped data access.
Designed for GKE horizontal scaling to support 1000+ LLM req/sec.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import hashlib
import secrets


class TenantTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantQuota(BaseModel):
    max_agents: int = 5
    max_tools: int = 10
    max_pipelines: int = 3
    max_rag_collections: int = 5
    max_documents_per_collection: int = 100
    max_users: int = 5
    max_api_keys: int = 3
    llm_requests_per_minute: int = 60
    llm_requests_per_day: int = 5000
    max_tokens_per_request: int = 4096
    max_concurrent_requests: int = 10
    storage_mb: int = 500


TIER_QUOTAS: Dict[TenantTier, TenantQuota] = {
    TenantTier.FREE: TenantQuota(
        max_agents=3, max_tools=5, max_pipelines=1, max_rag_collections=2,
        max_documents_per_collection=50, max_users=2, max_api_keys=1,
        llm_requests_per_minute=20, llm_requests_per_day=500,
        max_tokens_per_request=2048, max_concurrent_requests=2, storage_mb=100,
    ),
    TenantTier.STARTER: TenantQuota(
        max_agents=10, max_tools=25, max_pipelines=5, max_rag_collections=10,
        max_documents_per_collection=500, max_users=10, max_api_keys=5,
        llm_requests_per_minute=100, llm_requests_per_day=10000,
        max_tokens_per_request=4096, max_concurrent_requests=20, storage_mb=2000,
    ),
    TenantTier.PROFESSIONAL: TenantQuota(
        max_agents=50, max_tools=100, max_pipelines=20, max_rag_collections=50,
        max_documents_per_collection=2000, max_users=50, max_api_keys=20,
        llm_requests_per_minute=500, llm_requests_per_day=100000,
        max_tokens_per_request=8192, max_concurrent_requests=100, storage_mb=10000,
    ),
    TenantTier.ENTERPRISE: TenantQuota(
        max_agents=999, max_tools=999, max_pipelines=999, max_rag_collections=999,
        max_documents_per_collection=99999, max_users=999, max_api_keys=100,
        llm_requests_per_minute=5000, llm_requests_per_day=1000000,
        max_tokens_per_request=32768, max_concurrent_requests=1000, storage_mb=100000,
    ),
}


class Tenant(BaseModel):
    tenant_id: str = ""
    name: str = ""
    slug: str = ""
    tier: TenantTier = TenantTier.FREE
    quota: TenantQuota = Field(default_factory=TenantQuota)
    owner_email: str = ""
    domain: str = ""
    is_active: bool = True
    settings: Dict = Field(default_factory=dict)
    allowed_models: List[str] = Field(default_factory=list)
    allowed_providers: List[str] = Field(default_factory=list)
    api_keys: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Usage tracking
    current_agents: int = 0
    current_tools: int = 0
    current_users: int = 0
    llm_requests_today: int = 0
    llm_requests_this_minute: int = 0
    tokens_used_today: int = 0


class TenantManager:
    """
    Manages multi-tenant isolation, quotas, and lifecycle.
    PostgreSQL-backed with in-memory fallback.
    """

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._api_key_to_tenant: Dict[str, str] = {}
        self._slug_to_tenant: Dict[str, str] = {}
        self._db_available = False

    def _sf(self):
        from backend.db.sync_bridge import get_session_factory
        return get_session_factory()

    # ── Async DB helpers ──────────────────────────────────────────

    async def _db_create(self, tid, name, slug, tier, owner_email,
                         domain, settings_dict, allowed_providers,
                         quota_dict) -> Optional[Tenant]:
        factory = self._sf()
        if not factory:
            return None
        from backend.db.models import TenantModel
        async with factory() as session:
            row = TenantModel(
                id=tid, name=name, slug=slug, tier=tier.value,
                owner_email=owner_email, domain=domain,
                settings_json=settings_dict, quota_json=quota_dict,
                allowed_providers=allowed_providers,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._tenant_from_row(row)

    async def _db_get(self, tenant_id) -> Optional[Tenant]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import TenantModel
        async with factory() as session:
            row = (await session.execute(
                select(TenantModel).where(TenantModel.id == tenant_id)
            )).scalar_one_or_none()
            return self._tenant_from_row(row) if row else None

    async def _db_get_by_slug(self, slug) -> Optional[Tenant]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import TenantModel
        async with factory() as session:
            row = (await session.execute(
                select(TenantModel).where(TenantModel.slug == slug)
            )).scalar_one_or_none()
            return self._tenant_from_row(row) if row else None

    async def _db_list(self) -> List[Tenant]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import TenantModel
        async with factory() as session:
            rows = (await session.execute(
                select(TenantModel).order_by(TenantModel.created_at.desc())
            )).scalars().all()
            return [self._tenant_from_row(r) for r in rows]

    async def _db_update(self, tenant_id, **kwargs) -> Optional[Tenant]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import TenantModel
        async with factory() as session:
            row = (await session.execute(
                select(TenantModel).where(TenantModel.id == tenant_id)
            )).scalar_one_or_none()
            if not row:
                return None
            col_map = {"settings": "settings_json", "quota": "quota_json"}
            for k, v in kwargs.items():
                col = col_map.get(k, k)
                if k == "tier" and isinstance(v, TenantTier):
                    v = v.value
                if hasattr(row, col) and col not in ("id", "created_at"):
                    setattr(row, col, v)
            row.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(row)
            return self._tenant_from_row(row)

    async def _db_delete(self, tenant_id) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import TenantModel
        async with factory() as session:
            row = (await session.execute(
                select(TenantModel).where(TenantModel.id == tenant_id)
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def _db_stats(self) -> Dict:
        factory = self._sf()
        if not factory:
            return {}
        from sqlalchemy import select, func
        from backend.db.models import TenantModel
        async with factory() as session:
            total = (await session.execute(select(func.count(TenantModel.id)))).scalar() or 0
            active = (await session.execute(
                select(func.count(TenantModel.id)).where(TenantModel.is_active == True)
            )).scalar() or 0
            return {"total_tenants": total, "active_tenants": active, "persistence": "postgresql"}

    def _tenant_from_row(self, row) -> Tenant:
        tier = TenantTier(row.tier) if row.tier else TenantTier.FREE
        quota_data = row.quota_json if isinstance(row.quota_json, dict) else {}
        quota = TenantQuota(**quota_data) if quota_data else TIER_QUOTAS.get(tier, TenantQuota())
        settings = row.settings_json if isinstance(row.settings_json, dict) else {}
        providers = row.allowed_providers if isinstance(row.allowed_providers, list) else []
        return Tenant(
            tenant_id=row.id, name=row.name, slug=row.slug, tier=tier,
            quota=quota, owner_email=row.owner_email or "",
            domain=row.domain or "", is_active=row.is_active if row.is_active is not None else True,
            settings=settings, allowed_providers=providers,
            created_at=row.created_at or datetime.now(timezone.utc),
            updated_at=row.updated_at or datetime.now(timezone.utc),
        )

    # ── Public sync API ───────────────────────────────────────────

    def create(self, name: str, owner_email: str, tier: TenantTier = TenantTier.FREE,
               domain: str = "", settings: Dict = None) -> Tenant:
        slug = name.lower().replace(" ", "-").replace("_", "-")
        tid = f"tenant-{hashlib.md5(f'{slug}-{datetime.now().isoformat()}'.encode()).hexdigest()[:8]}"
        api_key = f"jai-{secrets.token_urlsafe(32)}"
        quota = TIER_QUOTAS[tier]
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_create(
                    tid, name, slug, tier, owner_email, domain,
                    settings or {}, ["google", "anthropic", "openai", "ollama"],
                    quota.model_dump(),
                ))
                if result:
                    result.api_keys = [api_key]
                    self._api_key_to_tenant[api_key] = tid
                    self._slug_to_tenant[slug] = tid
                    return result
            except Exception:
                pass
        t = Tenant(
            tenant_id=tid, name=name, slug=slug, tier=tier,
            quota=quota, owner_email=owner_email,
            domain=domain, settings=settings or {},
            api_keys=[api_key],
            allowed_providers=["google", "anthropic", "openai", "ollama"],
        )
        self._tenants[tid] = t
        self._slug_to_tenant[slug] = tid
        self._api_key_to_tenant[api_key] = tid
        return t

    def get(self, tenant_id: str) -> Optional[Tenant]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_get(tenant_id))
                if result:
                    return result
            except Exception:
                pass
        return self._tenants.get(tenant_id)

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_get_by_slug(slug))
                if result:
                    return result
            except Exception:
                pass
        tid = self._slug_to_tenant.get(slug)
        return self._tenants.get(tid) if tid else None

    def get_by_api_key(self, api_key: str) -> Optional[Tenant]:
        tid = self._api_key_to_tenant.get(api_key)
        if tid:
            return self.get(tid)
        return None

    def list_all(self) -> List[Tenant]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_list())
            except Exception:
                pass
        return list(self._tenants.values())

    def update(self, tenant_id: str, **kwargs) -> Optional[Tenant]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_update(tenant_id, **kwargs))
                if result:
                    if "tier" in kwargs:
                        result.quota = TIER_QUOTAS[TenantTier(kwargs["tier"])]
                    return result
            except Exception:
                pass
        t = self._tenants.get(tenant_id)
        if not t:
            return None
        for k, v in kwargs.items():
            if hasattr(t, k):
                setattr(t, k, v)
        if "tier" in kwargs:
            t.quota = TIER_QUOTAS[TenantTier(kwargs["tier"])]
        t.updated_at = datetime.now(timezone.utc)
        return t

    def delete(self, tenant_id: str) -> bool:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                ok = run_async(self._db_delete(tenant_id))
                if ok:
                    t = self._tenants.pop(tenant_id, None)
                    if t:
                        self._slug_to_tenant.pop(t.slug, None)
                        for key in t.api_keys:
                            self._api_key_to_tenant.pop(key, None)
                    return True
            except Exception:
                pass
        t = self._tenants.pop(tenant_id, None)
        if t:
            self._slug_to_tenant.pop(t.slug, None)
            for key in t.api_keys:
                self._api_key_to_tenant.pop(key, None)
            return True
        return False

    def generate_api_key(self, tenant_id: str) -> Optional[str]:
        t = self.get(tenant_id)
        if not t:
            return None
        if len(t.api_keys) >= t.quota.max_api_keys:
            return None
        key = f"jai-{secrets.token_urlsafe(32)}"
        t.api_keys.append(key)
        self._api_key_to_tenant[key] = tenant_id
        return key

    def revoke_api_key(self, tenant_id: str, api_key: str) -> bool:
        t = self.get(tenant_id)
        if not t or api_key not in t.api_keys:
            return False
        t.api_keys.remove(api_key)
        self._api_key_to_tenant.pop(api_key, None)
        return True

    def check_quota(self, tenant_id: str, resource: str) -> bool:
        t = self.get(tenant_id)
        if not t:
            return False
        checks = {
            "agents": t.current_agents < t.quota.max_agents,
            "tools": t.current_tools < t.quota.max_tools,
            "users": t.current_users < t.quota.max_users,
            "llm_request": t.llm_requests_this_minute < t.quota.llm_requests_per_minute,
            "llm_daily": t.llm_requests_today < t.quota.llm_requests_per_day,
        }
        return checks.get(resource, True)

    def record_llm_usage(self, tenant_id: str, tokens: int = 0):
        t = self.get(tenant_id)
        if t:
            t.llm_requests_today += 1
            t.llm_requests_this_minute += 1
            t.tokens_used_today += tokens

    def get_usage(self, tenant_id: str) -> Dict:
        t = self.get(tenant_id)
        if not t:
            return {}
        return {
            "tenant_id": tenant_id, "tier": t.tier.value,
            "agents": {"used": t.current_agents, "limit": t.quota.max_agents},
            "tools": {"used": t.current_tools, "limit": t.quota.max_tools},
            "users": {"used": t.current_users, "limit": t.quota.max_users},
            "llm_requests_today": {"used": t.llm_requests_today, "limit": t.quota.llm_requests_per_day},
            "llm_requests_per_minute": {"used": t.llm_requests_this_minute, "limit": t.quota.llm_requests_per_minute},
            "tokens_today": t.tokens_used_today,
        }

    def get_stats(self) -> Dict:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_stats())
                if result:
                    return result
            except Exception:
                pass
        return {
            "total_tenants": len(self._tenants),
            "by_tier": {tier.value: sum(1 for t in self._tenants.values() if t.tier == tier) for tier in TenantTier},
            "active_tenants": sum(1 for t in self._tenants.values() if t.is_active),
            "total_api_keys": sum(len(t.api_keys) for t in self._tenants.values()),
            "persistence": "in-memory" if not self._db_available else "postgresql",
        }
