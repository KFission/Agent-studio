"""
Environment Manager — Backend-enforced environment model.
Manages Dev/QA/UAT/Prod environments with:
- Per-environment variables (secrets, config)
- Asset promotion workflow with approvals
- Diffs between environments
- Rollback support
PostgreSQL-backed with in-memory fallback.
"""

import uuid
import copy
import hashlib
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Models
# ══════════════════════════════════════════════════════════════════════════════

class EnvironmentId(str, Enum):
    DEV = "dev"
    QA = "qa"
    UAT = "uat"
    PROD = "prod"


PROMOTION_ORDER = [EnvironmentId.DEV, EnvironmentId.QA, EnvironmentId.UAT, EnvironmentId.PROD]


class PromotionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"


class EnvVariable(BaseModel):
    """A single environment variable."""
    key: str
    value: str = ""
    is_secret: bool = False
    description: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = ""


class EnvironmentConfig(BaseModel):
    """Configuration for a single environment."""
    env_id: str  # dev, qa, uat, prod
    tenant_id: str = "tenant-default"
    label: str = ""
    description: str = ""
    variables: Dict[str, EnvVariable] = Field(default_factory=dict)
    is_locked: bool = False
    locked_by: str = ""
    locked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AssetSnapshot(BaseModel):
    """Snapshot of an asset at promotion time."""
    asset_type: str  # agent, prompt, pipeline, tool
    asset_id: str
    version: int = 1
    config_json: Dict[str, Any] = Field(default_factory=dict)
    checksum: str = ""


class PromotionRecord(BaseModel):
    """Record of an asset promotion between environments."""
    promotion_id: str = Field(default_factory=lambda: f"promo-{uuid.uuid4().hex[:8]}")
    tenant_id: str = "tenant-default"
    asset_type: str  # agent, prompt, pipeline, tool
    asset_id: str
    asset_name: str = ""
    from_env: str
    to_env: str
    from_version: int = 0
    to_version: int = 0
    status: PromotionStatus = PromotionStatus.PENDING
    requested_by: str = ""
    approved_by: str = ""
    rejected_by: str = ""
    rejection_reason: str = ""
    snapshot: Optional[AssetSnapshot] = None
    diff_summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# Environment Manager
# ══════════════════════════════════════════════════════════════════════════════

class EnvironmentManager:
    """
    Manages environment lifecycle, variables, promotions, and diffs.
    PostgreSQL-backed with in-memory fallback.
    """

    def __init__(self):
        # env configs: (tenant_id, env_id) -> EnvironmentConfig
        self._configs: Dict[str, EnvironmentConfig] = {}
        # promotions: promotion_id -> PromotionRecord
        self._promotions: Dict[str, PromotionRecord] = {}
        # asset snapshots per env: (tenant_id, env_id, asset_type, asset_id) -> AssetSnapshot
        self._deployed_assets: Dict[str, AssetSnapshot] = {}
        self._db_available = False

        # Initialize default environments
        for env_id in EnvironmentId:
            key = self._cfg_key("tenant-default", env_id.value)
            self._configs[key] = EnvironmentConfig(
                env_id=env_id.value, tenant_id="tenant-default",
                label=env_id.value.upper(),
                description=f"{env_id.value.upper()} environment",
            )

    def _cfg_key(self, tenant_id: str, env_id: str) -> str:
        return f"{tenant_id}:{env_id}"

    def _asset_key(self, tenant_id: str, env_id: str, asset_type: str, asset_id: str) -> str:
        return f"{tenant_id}:{env_id}:{asset_type}:{asset_id}"

    def _sf(self):
        from backend.db.sync_bridge import get_session_factory
        return get_session_factory()

    # ── Async DB helpers ──────────────────────────────────────────

    async def _db_save_config(self, cfg: EnvironmentConfig) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import EnvironmentConfigModel
        async with factory() as session:
            key = f"{cfg.tenant_id}:{cfg.env_id}"
            row = (await session.execute(
                select(EnvironmentConfigModel).where(EnvironmentConfigModel.id == key)
            )).scalar_one_or_none()
            vars_json = {k: v.model_dump(mode="json") for k, v in cfg.variables.items()}
            if row:
                row.label = cfg.label
                row.description = cfg.description
                row.variables_json = vars_json
                row.is_locked = cfg.is_locked
                row.locked_by = cfg.locked_by
                row.updated_at = datetime.utcnow()
            else:
                row = EnvironmentConfigModel(
                    id=key, env_id=cfg.env_id, tenant_id=cfg.tenant_id,
                    label=cfg.label, description=cfg.description,
                    variables_json=vars_json, is_locked=cfg.is_locked,
                    locked_by=cfg.locked_by,
                )
                session.add(row)
            await session.commit()
            return True

    async def _db_save_promotion(self, promo: PromotionRecord) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import PromotionRecordModel
        async with factory() as session:
            row = (await session.execute(
                select(PromotionRecordModel).where(PromotionRecordModel.id == promo.promotion_id)
            )).scalar_one_or_none()
            data = {
                "tenant_id": promo.tenant_id,
                "asset_type": promo.asset_type, "asset_id": promo.asset_id,
                "asset_name": promo.asset_name,
                "from_env": promo.from_env, "to_env": promo.to_env,
                "from_version": promo.from_version, "to_version": promo.to_version,
                "status": promo.status.value,
                "requested_by": promo.requested_by, "approved_by": promo.approved_by,
                "rejected_by": promo.rejected_by, "rejection_reason": promo.rejection_reason,
                "snapshot_json": promo.snapshot.model_dump(mode="json") if promo.snapshot else None,
                "diff_json": promo.diff_summary,
                "resolved_at": promo.resolved_at, "deployed_at": promo.deployed_at,
                "metadata_json": promo.metadata,
            }
            if row:
                for k, v in data.items():
                    setattr(row, k, v)
            else:
                row = PromotionRecordModel(id=promo.promotion_id, **data)
                session.add(row)
            await session.commit()
            return True

    async def _db_list_promotions(self, tenant_id, env_id=None, status=None, limit=50) -> List[Dict]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import PromotionRecordModel
        async with factory() as session:
            q = select(PromotionRecordModel).where(PromotionRecordModel.tenant_id == tenant_id)
            if env_id:
                q = q.where(PromotionRecordModel.to_env == env_id)
            if status:
                q = q.where(PromotionRecordModel.status == status)
            q = q.order_by(PromotionRecordModel.created_at.desc()).limit(limit)
            rows = (await session.execute(q)).scalars().all()
            return [{"promotion_id": r.id, "asset_type": r.asset_type, "asset_id": r.asset_id,
                      "from_env": r.from_env, "to_env": r.to_env, "status": r.status,
                      "requested_by": r.requested_by, "created_at": r.created_at.isoformat() if r.created_at else None}
                     for r in rows]

    # ── Environment CRUD ──────────────────────────────────────────

    def get_environments(self, tenant_id: str = "tenant-default") -> List[EnvironmentConfig]:
        """Get all environments for a tenant."""
        return [c for c in self._configs.values() if c.tenant_id == tenant_id]

    def get_environment(self, env_id: str, tenant_id: str = "tenant-default") -> Optional[EnvironmentConfig]:
        """Get a single environment config."""
        return self._configs.get(self._cfg_key(tenant_id, env_id))

    def ensure_environments(self, tenant_id: str) -> List[EnvironmentConfig]:
        """Ensure all 4 environments exist for a tenant."""
        configs = []
        for env in EnvironmentId:
            key = self._cfg_key(tenant_id, env.value)
            if key not in self._configs:
                cfg = EnvironmentConfig(
                    env_id=env.value, tenant_id=tenant_id,
                    label=env.value.upper(),
                    description=f"{env.value.upper()} environment",
                )
                self._configs[key] = cfg
            configs.append(self._configs[key])
        return configs

    # ── Environment Variables ─────────────────────────────────────

    def set_variable(self, env_id: str, key: str, value: str,
                     is_secret: bool = False, description: str = "",
                     updated_by: str = "admin",
                     tenant_id: str = "tenant-default") -> Optional[EnvVariable]:
        """Set an environment variable."""
        cfg = self.get_environment(env_id, tenant_id)
        if not cfg:
            return None
        if cfg.is_locked:
            logger.warning(f"Cannot set var on locked env {env_id}")
            return None

        var = EnvVariable(
            key=key, value=value, is_secret=is_secret,
            description=description, updated_by=updated_by,
        )
        cfg.variables[key] = var
        cfg.updated_at = datetime.utcnow()

        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_save_config(cfg))
            except Exception:
                pass
        return var

    def get_variable(self, env_id: str, key: str,
                     tenant_id: str = "tenant-default") -> Optional[EnvVariable]:
        """Get a single environment variable."""
        cfg = self.get_environment(env_id, tenant_id)
        if not cfg:
            return None
        return cfg.variables.get(key)

    def get_variables(self, env_id: str, tenant_id: str = "tenant-default",
                      include_secrets: bool = False) -> Dict[str, Any]:
        """Get all variables for an environment."""
        cfg = self.get_environment(env_id, tenant_id)
        if not cfg:
            return {}
        result = {}
        for k, v in cfg.variables.items():
            val = v.value if (include_secrets or not v.is_secret) else "••••••••"
            result[k] = {
                "key": k, "value": val, "is_secret": v.is_secret,
                "description": v.description, "updated_by": v.updated_by,
                "updated_at": v.updated_at.isoformat(),
            }
        return result

    def delete_variable(self, env_id: str, key: str,
                        tenant_id: str = "tenant-default") -> bool:
        """Delete an environment variable."""
        cfg = self.get_environment(env_id, tenant_id)
        if not cfg or cfg.is_locked:
            return False
        removed = cfg.variables.pop(key, None)
        if removed:
            cfg.updated_at = datetime.utcnow()
            if self._db_available:
                from backend.db.sync_bridge import run_async
                try:
                    run_async(self._db_save_config(cfg))
                except Exception:
                    pass
        return removed is not None

    def bulk_set_variables(self, env_id: str, variables: Dict[str, str],
                           updated_by: str = "admin",
                           tenant_id: str = "tenant-default") -> int:
        """Set multiple variables at once."""
        count = 0
        for k, v in variables.items():
            if self.set_variable(env_id, k, v, updated_by=updated_by, tenant_id=tenant_id):
                count += 1
        return count

    # ── Environment Locking ───────────────────────────────────────

    def lock_environment(self, env_id: str, locked_by: str = "admin",
                         tenant_id: str = "tenant-default") -> bool:
        """Lock an environment to prevent changes."""
        cfg = self.get_environment(env_id, tenant_id)
        if not cfg:
            return False
        cfg.is_locked = True
        cfg.locked_by = locked_by
        cfg.locked_at = datetime.utcnow()
        return True

    def unlock_environment(self, env_id: str, tenant_id: str = "tenant-default") -> bool:
        """Unlock an environment."""
        cfg = self.get_environment(env_id, tenant_id)
        if not cfg:
            return False
        cfg.is_locked = False
        cfg.locked_by = ""
        cfg.locked_at = None
        return True

    # ── Asset Promotion ───────────────────────────────────────────

    def _compute_checksum(self, config_json: Dict) -> str:
        """Compute a stable checksum for a config dict."""
        import json
        canonical = json.dumps(config_json, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def request_promotion(
        self, asset_type: str, asset_id: str, asset_name: str,
        from_env: str, to_env: str,
        config_json: Dict[str, Any],
        from_version: int = 0, to_version: int = 0,
        requested_by: str = "admin",
        tenant_id: str = "tenant-default",
    ) -> PromotionRecord:
        """Request promotion of an asset from one environment to another."""
        # Validate promotion order
        from_idx = next((i for i, e in enumerate(PROMOTION_ORDER) if e.value == from_env), -1)
        to_idx = next((i for i, e in enumerate(PROMOTION_ORDER) if e.value == to_env), -1)
        if to_idx <= from_idx:
            raise ValueError(f"Cannot promote from {from_env} to {to_env} — must follow dev→qa→uat→prod order")

        snapshot = AssetSnapshot(
            asset_type=asset_type, asset_id=asset_id,
            version=to_version or from_version,
            config_json=config_json,
            checksum=self._compute_checksum(config_json),
        )

        # Auto-compute diff if asset exists in target env
        diff = self._compute_diff(tenant_id, to_env, asset_type, asset_id, config_json)

        # Auto-approve for dev→qa (no approval needed)
        auto_approve = to_env in ("qa",)
        status = PromotionStatus.APPROVED if auto_approve else PromotionStatus.PENDING

        promo = PromotionRecord(
            tenant_id=tenant_id, asset_type=asset_type, asset_id=asset_id,
            asset_name=asset_name, from_env=from_env, to_env=to_env,
            from_version=from_version, to_version=to_version or from_version,
            status=status, requested_by=requested_by,
            approved_by=requested_by if auto_approve else "",
            snapshot=snapshot, diff_summary=diff,
        )

        self._promotions[promo.promotion_id] = promo

        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_save_promotion(promo))
            except Exception:
                pass

        # Auto-deploy if approved
        if status == PromotionStatus.APPROVED:
            self._deploy_promotion(promo)

        return promo

    def approve_promotion(self, promotion_id: str, approved_by: str = "admin") -> Optional[PromotionRecord]:
        """Approve a pending promotion."""
        promo = self._promotions.get(promotion_id)
        if not promo or promo.status != PromotionStatus.PENDING:
            return None
        promo.status = PromotionStatus.APPROVED
        promo.approved_by = approved_by
        promo.resolved_at = datetime.utcnow()

        # Deploy the promotion
        self._deploy_promotion(promo)

        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_save_promotion(promo))
            except Exception:
                pass
        return promo

    def reject_promotion(self, promotion_id: str, rejected_by: str = "admin",
                         reason: str = "") -> Optional[PromotionRecord]:
        """Reject a pending promotion."""
        promo = self._promotions.get(promotion_id)
        if not promo or promo.status != PromotionStatus.PENDING:
            return None
        promo.status = PromotionStatus.REJECTED
        promo.rejected_by = rejected_by
        promo.rejection_reason = reason
        promo.resolved_at = datetime.utcnow()

        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_save_promotion(promo))
            except Exception:
                pass
        return promo

    def _deploy_promotion(self, promo: PromotionRecord):
        """Deploy a promotion — store asset snapshot in target environment."""
        if not promo.snapshot:
            return
        key = self._asset_key(promo.tenant_id, promo.to_env, promo.asset_type, promo.asset_id)
        self._deployed_assets[key] = promo.snapshot
        promo.status = PromotionStatus.DEPLOYED
        promo.deployed_at = datetime.utcnow()

    def rollback_promotion(self, promotion_id: str, rolled_back_by: str = "admin") -> Optional[PromotionRecord]:
        """Roll back a deployed promotion."""
        promo = self._promotions.get(promotion_id)
        if not promo or promo.status != PromotionStatus.DEPLOYED:
            return None

        # Remove from deployed assets
        key = self._asset_key(promo.tenant_id, promo.to_env, promo.asset_type, promo.asset_id)
        self._deployed_assets.pop(key, None)

        promo.status = PromotionStatus.ROLLED_BACK
        promo.metadata["rolled_back_by"] = rolled_back_by
        promo.metadata["rolled_back_at"] = datetime.utcnow().isoformat()

        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_save_promotion(promo))
            except Exception:
                pass
        return promo

    # ── Diffs ─────────────────────────────────────────────────────

    def _compute_diff(self, tenant_id: str, to_env: str,
                      asset_type: str, asset_id: str,
                      new_config: Dict) -> Dict[str, Any]:
        """Compute diff between current deployed version and new config."""
        key = self._asset_key(tenant_id, to_env, asset_type, asset_id)
        existing = self._deployed_assets.get(key)

        if not existing:
            return {"type": "new", "message": f"New asset in {to_env} — no previous version"}

        old = existing.config_json
        added = {k: v for k, v in new_config.items() if k not in old}
        removed = {k: v for k, v in old.items() if k not in new_config}
        changed = {
            k: {"old": old[k], "new": new_config[k]}
            for k in old if k in new_config and old[k] != new_config[k]
        }

        return {
            "type": "update",
            "added_keys": list(added.keys()),
            "removed_keys": list(removed.keys()),
            "changed_keys": list(changed.keys()),
            "changes": changed,
            "old_checksum": existing.checksum,
            "new_checksum": self._compute_checksum(new_config),
        }

    def diff_environments(self, env_a: str, env_b: str, asset_type: Optional[str] = None,
                          tenant_id: str = "tenant-default") -> Dict[str, Any]:
        """Compare all deployed assets between two environments."""
        prefix_a = f"{tenant_id}:{env_a}:"
        prefix_b = f"{tenant_id}:{env_b}:"

        assets_a = {k[len(prefix_a):]: v for k, v in self._deployed_assets.items()
                     if k.startswith(prefix_a) and (not asset_type or v.asset_type == asset_type)}
        assets_b = {k[len(prefix_b):]: v for k, v in self._deployed_assets.items()
                     if k.startswith(prefix_b) and (not asset_type or v.asset_type == asset_type)}

        only_in_a = [k for k in assets_a if k not in assets_b]
        only_in_b = [k for k in assets_b if k not in assets_a]
        in_both = [k for k in assets_a if k in assets_b]

        diffs = []
        for k in in_both:
            if assets_a[k].checksum != assets_b[k].checksum:
                diffs.append({
                    "asset": k,
                    "version_a": assets_a[k].version,
                    "version_b": assets_b[k].version,
                    "checksum_a": assets_a[k].checksum,
                    "checksum_b": assets_b[k].checksum,
                })

        return {
            "env_a": env_a, "env_b": env_b,
            f"only_in_{env_a}": only_in_a,
            f"only_in_{env_b}": only_in_b,
            "different": diffs,
            "identical": len(in_both) - len(diffs),
        }

    # ── Queries ───────────────────────────────────────────────────

    def get_promotion(self, promotion_id: str) -> Optional[PromotionRecord]:
        return self._promotions.get(promotion_id)

    def list_promotions(self, tenant_id: str = "tenant-default",
                        env_id: Optional[str] = None,
                        status: Optional[str] = None,
                        limit: int = 50) -> List[PromotionRecord]:
        promos = [p for p in self._promotions.values() if p.tenant_id == tenant_id]
        if env_id:
            promos = [p for p in promos if p.to_env == env_id]
        if status:
            promos = [p for p in promos if p.status.value == status]
        promos.sort(key=lambda p: p.created_at, reverse=True)
        return promos[:limit]

    def get_deployed_asset(self, env_id: str, asset_type: str, asset_id: str,
                           tenant_id: str = "tenant-default") -> Optional[AssetSnapshot]:
        key = self._asset_key(tenant_id, env_id, asset_type, asset_id)
        return self._deployed_assets.get(key)

    def list_deployed_assets(self, env_id: str, asset_type: Optional[str] = None,
                             tenant_id: str = "tenant-default") -> List[Dict[str, Any]]:
        prefix = f"{tenant_id}:{env_id}:"
        results = []
        for k, v in self._deployed_assets.items():
            if k.startswith(prefix) and (not asset_type or v.asset_type == asset_type):
                results.append({
                    "asset_type": v.asset_type, "asset_id": v.asset_id,
                    "version": v.version, "checksum": v.checksum,
                })
        return results

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self, tenant_id: str = "tenant-default") -> Dict[str, Any]:
        envs = self.get_environments(tenant_id)
        promos = [p for p in self._promotions.values() if p.tenant_id == tenant_id]
        return {
            "environments": len(envs),
            "total_promotions": len(promos),
            "pending_approvals": len([p for p in promos if p.status == PromotionStatus.PENDING]),
            "deployed": len([p for p in promos if p.status == PromotionStatus.DEPLOYED]),
            "deployed_assets_by_env": {
                env.value: len(self.list_deployed_assets(env.value, tenant_id=tenant_id))
                for env in EnvironmentId
            },
            "variables_by_env": {
                cfg.env_id: len(cfg.variables) for cfg in envs
            },
        }
