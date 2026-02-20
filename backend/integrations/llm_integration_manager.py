"""
LLM Integration Manager — Admin-managed LLM provider integrations.
Admins create integrations (provider + API key / service account + config)
and push them to groups so developers can use LLMs without managing keys.
DB-backed with in-memory cache for fast reads.
"""

import uuid
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"


class IntegrationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class LLMIntegration(BaseModel):
    """An admin-configured LLM provider integration."""
    integration_id: str = Field(default_factory=lambda: f"int-{uuid.uuid4().hex[:8]}")
    name: str  # e.g. "OpenAI Production", "Gemini Dev"
    provider: LLMProvider
    description: str = ""

    # Auth
    auth_type: str = "api_key"  # api_key | service_account
    api_key: str = ""
    api_key_masked: str = ""  # e.g. "sk-...abc123"
    service_account_json: Dict[str, Any] = Field(default_factory=dict)
    endpoint_url: str = ""  # custom endpoint for Azure, Ollama, etc.
    project_id: str = ""  # GCP project for Google/Vertex

    # Config
    default_model: str = ""  # default model for this integration
    allowed_models: List[str] = Field(default_factory=list)
    registered_models: List[str] = Field(default_factory=list)  # models registered in ModelLibrary
    max_tokens_per_request: int = 0  # 0 = unlimited
    rate_limit_rpm: int = 0  # requests per minute, 0 = unlimited

    # Group assignment
    assigned_group_ids: List[str] = Field(default_factory=list)

    # Status
    status: IntegrationStatus = IntegrationStatus.ACTIVE
    last_tested: Optional[datetime] = None
    last_error: str = ""

    # Metadata
    created_by: str = "admin"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMIntegrationManager:
    """
    Manages LLM provider integrations that admins create and push to groups.
    In-memory cache + DB write-through for persistence.
    """

    def __init__(self):
        self._integrations: Dict[str, LLMIntegration] = {}
        self._db_available = False

    # ── DB helpers ────────────────────────────────────────────────

    def _get_session_factory(self):
        from backend.db.engine import get_session_factory
        return get_session_factory()

    async def _db_save(self, integration: LLMIntegration):
        """Insert or upsert integration into PostgreSQL."""
        if not self._db_available:
            return
        try:
            from sqlalchemy import select
            from backend.db.models import IntegrationModel
            factory = self._get_session_factory()
            async with factory() as session:
                result = await session.execute(
                    select(IntegrationModel).where(IntegrationModel.id == integration.integration_id)
                )
                row = result.scalar_one_or_none()
                if row:
                    row.name = integration.name
                    row.provider = integration.provider.value
                    row.description = integration.description
                    row.auth_type = integration.auth_type
                    from backend.utils.crypto import encrypt, encrypt_json
                    row.api_key_encrypted = encrypt(integration.api_key) if integration.api_key else ""
                    row.api_key_masked = integration.api_key_masked
                    row.service_account_json_encrypted = encrypt_json(integration.service_account_json) if integration.service_account_json else ""
                    row.endpoint_url = integration.endpoint_url
                    row.project_id = integration.project_id
                    row.default_model = integration.default_model
                    row.allowed_models = integration.allowed_models
                    row.registered_models = integration.registered_models
                    row.rate_limit_rpm = integration.rate_limit_rpm
                    row.assigned_group_ids = integration.assigned_group_ids
                    row.status = integration.status.value
                    row.last_tested = integration.last_tested
                    row.last_error = integration.last_error
                    row.updated_at = datetime.utcnow()
                else:
                    row = IntegrationModel(
                        id=integration.integration_id,
                        name=integration.name,
                        provider=integration.provider.value,
                        description=integration.description,
                        auth_type=integration.auth_type,
                        api_key_encrypted=encrypt(integration.api_key) if integration.api_key else "",
                        api_key_masked=integration.api_key_masked,
                        service_account_json_encrypted=encrypt_json(integration.service_account_json) if integration.service_account_json else "",
                        endpoint_url=integration.endpoint_url,
                        project_id=integration.project_id,
                        default_model=integration.default_model,
                        allowed_models=integration.allowed_models,
                        registered_models=integration.registered_models,
                        rate_limit_rpm=integration.rate_limit_rpm,
                        assigned_group_ids=integration.assigned_group_ids,
                        status=integration.status.value,
                        last_tested=integration.last_tested,
                        last_error=integration.last_error,
                        created_by=integration.created_by,
                    )
                    session.add(row)
                await session.commit()
        except Exception as e:
            logger.error(f"DB save integration failed: {e}")

    async def _db_delete(self, integration_id: str):
        if not self._db_available:
            return
        try:
            from sqlalchemy import delete as sa_delete
            from backend.db.models import IntegrationModel
            factory = self._get_session_factory()
            async with factory() as session:
                await session.execute(sa_delete(IntegrationModel).where(IntegrationModel.id == integration_id))
                await session.commit()
        except Exception as e:
            logger.error(f"DB delete integration failed: {e}")

    async def hydrate_from_db(self, session):
        """Load integrations from DB into in-memory cache."""
        from sqlalchemy import select
        from backend.db.models import IntegrationModel
        from backend.utils.crypto import decrypt, decrypt_json
        rows = (await session.execute(select(IntegrationModel))).scalars().all()
        for r in rows:
            if r.id not in self._integrations:
                # Decrypt secrets — decrypt() gracefully handles unencrypted legacy values
                raw_key = decrypt(r.api_key_encrypted) if r.api_key_encrypted else ""
                sa_json = decrypt_json(r.service_account_json_encrypted) if getattr(r, "service_account_json_encrypted", None) else (r.service_account_json or {})
                self._integrations[r.id] = LLMIntegration(
                    integration_id=r.id,
                    name=r.name,
                    provider=LLMProvider(r.provider),
                    description=r.description or "",
                    auth_type=r.auth_type or "api_key",
                    api_key=raw_key,
                    api_key_masked=r.api_key_masked or "",
                    service_account_json=sa_json,
                    endpoint_url=r.endpoint_url or "",
                    project_id=r.project_id or "",
                    default_model=r.default_model or "",
                    allowed_models=r.allowed_models or [],
                    registered_models=r.registered_models or [],
                    rate_limit_rpm=r.rate_limit_rpm or 0,
                    assigned_group_ids=r.assigned_group_ids or [],
                    status=IntegrationStatus(r.status) if r.status in [s.value for s in IntegrationStatus] else IntegrationStatus.ACTIVE,
                    last_tested=r.last_tested,
                    last_error=r.last_error or "",
                    created_by=r.created_by or "admin",
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
        print(f"[JAI AGENT OS]   Hydrated {len(rows)} integrations from DB")

    # ── CRUD ─────────────────────────────────────────────────────

    @staticmethod
    def _mask_key(key: str) -> str:
        if not key or len(key) < 8:
            return "***"
        return key[:4] + "..." + key[-4:]

    def create(
        self,
        name: str,
        provider: str,
        api_key: str = "",
        description: str = "",
        endpoint_url: str = "",
        project_id: str = "",
        default_model: str = "",
        allowed_models: Optional[List[str]] = None,
        registered_models: Optional[List[str]] = None,
        rate_limit_rpm: int = 0,
        assigned_group_ids: Optional[List[str]] = None,
        created_by: str = "admin",
        auth_type: str = "api_key",
        service_account_json: Optional[Dict[str, Any]] = None,
    ) -> LLMIntegration:
        integration = LLMIntegration(
            name=name,
            provider=LLMProvider(provider),
            auth_type=auth_type,
            api_key=api_key,
            api_key_masked=self._mask_key(api_key) if api_key else ("service-acct" if auth_type == "service_account" else "***"),
            service_account_json=service_account_json or {},
            description=description,
            endpoint_url=endpoint_url,
            project_id=project_id,
            default_model=default_model,
            allowed_models=allowed_models or [],
            registered_models=registered_models or [],
            rate_limit_rpm=rate_limit_rpm,
            assigned_group_ids=assigned_group_ids or [],
            created_by=created_by,
        )
        self._integrations[integration.integration_id] = integration
        return integration

    async def create_async(self, **kwargs) -> LLMIntegration:
        integration = self.create(**kwargs)
        await self._db_save(integration)
        return integration

    def get(self, integration_id: str) -> Optional[LLMIntegration]:
        return self._integrations.get(integration_id)

    def update(self, integration_id: str, **kwargs) -> Optional[LLMIntegration]:
        integration = self._integrations.get(integration_id)
        if not integration:
            return None
        for k, v in kwargs.items():
            if hasattr(integration, k) and k not in ("integration_id", "created_at"):
                setattr(integration, k, v)
        if "api_key" in kwargs and kwargs["api_key"]:
            integration.api_key_masked = self._mask_key(kwargs["api_key"])
        integration.updated_at = datetime.utcnow()
        return integration

    async def update_async(self, integration_id: str, **kwargs) -> Optional[LLMIntegration]:
        integration = self.update(integration_id, **kwargs)
        if integration:
            await self._db_save(integration)
        return integration

    def delete(self, integration_id: str) -> bool:
        return self._integrations.pop(integration_id, None) is not None

    async def delete_async(self, integration_id: str) -> bool:
        ok = self.delete(integration_id)
        if ok:
            await self._db_delete(integration_id)
        return ok

    def list_all(self) -> List[LLMIntegration]:
        return sorted(self._integrations.values(), key=lambda i: i.created_at, reverse=True)

    def list_by_provider(self, provider: str) -> List[LLMIntegration]:
        return [i for i in self._integrations.values() if i.provider.value == provider]

    # ── Group assignment ──────────────────────────────────────────

    def push_to_groups(self, integration_id: str, group_ids: List[str]) -> bool:
        integration = self._integrations.get(integration_id)
        if not integration:
            return False
        integration.assigned_group_ids = list(set(integration.assigned_group_ids + group_ids))
        integration.updated_at = datetime.utcnow()
        return True

    async def push_to_groups_async(self, integration_id: str, group_ids: List[str]) -> bool:
        ok = self.push_to_groups(integration_id, group_ids)
        if ok:
            await self._db_save(self._integrations[integration_id])
        return ok

    def revoke_from_groups(self, integration_id: str, group_ids: List[str]) -> bool:
        integration = self._integrations.get(integration_id)
        if not integration:
            return False
        integration.assigned_group_ids = [g for g in integration.assigned_group_ids if g not in group_ids]
        integration.updated_at = datetime.utcnow()
        return True

    async def revoke_from_groups_async(self, integration_id: str, group_ids: List[str]) -> bool:
        ok = self.revoke_from_groups(integration_id, group_ids)
        if ok:
            await self._db_save(self._integrations[integration_id])
        return ok

    def get_group_integrations(self, group_id: str) -> List[LLMIntegration]:
        """Get all integrations available to a group."""
        return [i for i in self._integrations.values() if group_id in i.assigned_group_ids and i.status == IntegrationStatus.ACTIVE]

    def get_user_integrations(self, user_group_ids: List[str]) -> List[LLMIntegration]:
        """Get all integrations available to a user via their group memberships."""
        result = []
        seen = set()
        for i in self._integrations.values():
            if i.status != IntegrationStatus.ACTIVE:
                continue
            for gid in user_group_ids:
                if gid in i.assigned_group_ids and i.integration_id not in seen:
                    result.append(i)
                    seen.add(i.integration_id)
        return result

    # ── Test / Status ─────────────────────────────────────────────

    def mark_tested(self, integration_id: str, success: bool, error: str = "") -> Optional[LLMIntegration]:
        integration = self._integrations.get(integration_id)
        if not integration:
            return None
        integration.last_tested = datetime.utcnow()
        integration.status = IntegrationStatus.ACTIVE if success else IntegrationStatus.ERROR
        integration.last_error = error if not success else ""
        return integration

    async def mark_tested_async(self, integration_id: str, success: bool, error: str = "") -> Optional[LLMIntegration]:
        integration = self.mark_tested(integration_id, success, error)
        if integration:
            await self._db_save(integration)
        return integration

    def to_safe_list(self) -> List[Dict[str, Any]]:
        """Return integrations without exposing raw API keys or service account JSON."""
        result = []
        for i in self._integrations.values():
            d = i.model_dump(mode="json")
            d.pop("api_key", None)
            d.pop("service_account_json", None)
            result.append(d)
        return result

    def get_safe(self, integration_id: str) -> Optional[Dict[str, Any]]:
        i = self._integrations.get(integration_id)
        if not i:
            return None
        d = i.model_dump(mode="json")
        d.pop("api_key", None)
        d.pop("service_account_json", None)
        return d

    def get_stats(self) -> Dict[str, Any]:
        integrations = list(self._integrations.values())
        return {
            "total": len(integrations),
            "active": sum(1 for i in integrations if i.status == IntegrationStatus.ACTIVE),
            "by_provider": {p.value: sum(1 for i in integrations if i.provider == p) for p in LLMProvider if any(i.provider == p for i in integrations)},
            "total_groups_served": len(set(g for i in integrations for g in i.assigned_group_ids)),
        }
