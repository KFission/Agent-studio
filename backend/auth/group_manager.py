"""
Group Manager — PostgreSQL-backed with in-memory fallback.
LoB / Team-based access control for JAI Agent OS.
"""

import uuid
import logging
from typing import Optional, Dict, List, Set, Any
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Group(BaseModel):
    """A group represents a team or Line of Business."""
    group_id: str = Field(default_factory=lambda: f"grp-{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    lob: str = ""
    owner_id: str = ""
    member_ids: List[str] = Field(default_factory=list)
    allowed_model_ids: List[str] = Field(default_factory=list)
    allowed_agent_ids: List[str] = Field(default_factory=list)
    assigned_roles: List[str] = Field(default_factory=list)
    monthly_budget_usd: float = 0
    daily_token_limit: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _group_from_row(row) -> Group:
    return Group(
        group_id=row.id, name=row.name, description=row.description or "",
        lob=row.lob or "", owner_id=row.owner_id or "",
        member_ids=row.member_ids if isinstance(row.member_ids, list) else [],
        allowed_model_ids=row.allowed_model_ids if isinstance(row.allowed_model_ids, list) else [],
        allowed_agent_ids=row.allowed_agent_ids if isinstance(row.allowed_agent_ids, list) else [],
        assigned_roles=row.assigned_roles if isinstance(row.assigned_roles, list) else [],
        monthly_budget_usd=row.monthly_budget_usd or 0,
        daily_token_limit=row.daily_token_limit or 0,
        is_active=row.is_active if row.is_active is not None else True,
        created_at=row.created_at or datetime.utcnow(),
        updated_at=row.updated_at or datetime.utcnow(),
        metadata=row.metadata_json if isinstance(row.metadata_json, dict) else {},
    )


class GroupManager:
    """
    Manages groups (teams/LoB) with model, agent, and role assignment.
    PostgreSQL-backed with in-memory fallback.
    """

    def __init__(self):
        self._groups: Dict[str, Group] = {}
        self._user_group_index: Dict[str, Set[str]] = {}
        self._db_available = False

    def _sf(self):
        from backend.db.sync_bridge import get_session_factory
        return get_session_factory()

    # ── Async DB helpers ──────────────────────────────────────────

    async def _db_create(self, name, description, lob, owner_id,
                         allowed_model_ids, allowed_agent_ids,
                         assigned_roles, monthly_budget_usd) -> Optional[Group]:
        factory = self._sf()
        if not factory:
            return None
        from backend.db.models import GroupModel
        async with factory() as session:
            row = GroupModel(
                name=name, description=description, lob=lob, owner_id=owner_id,
                member_ids=[], allowed_model_ids=allowed_model_ids,
                allowed_agent_ids=allowed_agent_ids, assigned_roles=assigned_roles,
                monthly_budget_usd=monthly_budget_usd,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _group_from_row(row)

    async def _db_get(self, group_id) -> Optional[Group]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import GroupModel
        async with factory() as session:
            row = (await session.execute(
                select(GroupModel).where(GroupModel.id == group_id)
            )).scalar_one_or_none()
            return _group_from_row(row) if row else None

    async def _db_update(self, group_id, **kwargs) -> Optional[Group]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import GroupModel
        async with factory() as session:
            row = (await session.execute(
                select(GroupModel).where(GroupModel.id == group_id)
            )).scalar_one_or_none()
            if not row:
                return None
            for k, v in kwargs.items():
                col = "metadata_json" if k == "metadata" else k
                if hasattr(row, col) and col not in ("id", "created_at"):
                    setattr(row, col, v)
            row.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(row)
            return _group_from_row(row)

    async def _db_delete(self, group_id) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import GroupModel
        async with factory() as session:
            row = (await session.execute(
                select(GroupModel).where(GroupModel.id == group_id)
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def _db_list(self) -> List[Group]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import GroupModel
        async with factory() as session:
            rows = (await session.execute(
                select(GroupModel).order_by(GroupModel.created_at.desc())
            )).scalars().all()
            return [_group_from_row(r) for r in rows]

    async def _db_stats(self) -> Dict[str, Any]:
        factory = self._sf()
        if not factory:
            return {}
        from sqlalchemy import select, func
        from backend.db.models import GroupModel
        async with factory() as session:
            total = (await session.execute(select(func.count(GroupModel.id)))).scalar() or 0
            active = (await session.execute(
                select(func.count(GroupModel.id)).where(GroupModel.is_active == True)
            )).scalar() or 0
            return {"total_groups": total, "active_groups": active, "persistence": "postgresql"}

    # ── Public sync API ───────────────────────────────────────────

    def create(self, name, description="", lob="", owner_id="admin",
               allowed_model_ids=None, allowed_agent_ids=None,
               assigned_roles=None, monthly_budget_usd=0) -> Group:
        ami = allowed_model_ids or []
        aai = allowed_agent_ids or []
        ar = assigned_roles or ["agent_developer"]
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_create(
                    name, description, lob, owner_id, ami, aai, ar, monthly_budget_usd
                ))
                if result:
                    return result
            except Exception as e:
                logger.warning(f"DB group create failed: {e}")
        group = Group(name=name, description=description, lob=lob, owner_id=owner_id,
                      allowed_model_ids=ami, allowed_agent_ids=aai,
                      assigned_roles=ar, monthly_budget_usd=monthly_budget_usd)
        self._groups[group.group_id] = group
        return group

    def get(self, group_id) -> Optional[Group]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_get(group_id))
            except Exception:
                pass
        return self._groups.get(group_id)

    def get_by_name(self, name) -> Optional[Group]:
        for g in self.list_all():
            if g.name.lower() == name.lower():
                return g
        return None

    def update(self, group_id, **kwargs) -> Optional[Group]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_update(group_id, **kwargs))
                if result:
                    return result
            except Exception:
                pass
        group = self._groups.get(group_id)
        if not group:
            return None
        for k, v in kwargs.items():
            if hasattr(group, k) and k not in ("group_id", "created_at"):
                setattr(group, k, v)
        group.updated_at = datetime.utcnow()
        return group

    def delete(self, group_id) -> bool:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_delete(group_id))
            except Exception:
                pass
        group = self._groups.pop(group_id, None)
        if group:
            for uid in group.member_ids:
                if uid in self._user_group_index:
                    self._user_group_index[uid].discard(group_id)
            return True
        return False

    def list_all(self) -> List[Group]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_list())
            except Exception:
                pass
        return sorted(self._groups.values(), key=lambda g: g.created_at, reverse=True)

    # ── Member Management ─────────────────────────────────────────

    def add_member(self, group_id, user_id) -> bool:
        group = self.get(group_id)
        if not group:
            return False
        if user_id not in group.member_ids:
            members = list(group.member_ids) + [user_id]
            self.update(group_id, member_ids=members)
        if user_id not in self._user_group_index:
            self._user_group_index[user_id] = set()
        self._user_group_index[user_id].add(group_id)
        return True

    def remove_member(self, group_id, user_id) -> bool:
        group = self.get(group_id)
        if not group:
            return False
        members = [m for m in group.member_ids if m != user_id]
        self.update(group_id, member_ids=members)
        if user_id in self._user_group_index:
            self._user_group_index[user_id].discard(group_id)
        return True

    def get_user_groups(self, user_id) -> List[Group]:
        all_groups = self.list_all()
        return [g for g in all_groups if user_id in g.member_ids]

    def get_group_members(self, group_id) -> List[str]:
        group = self.get(group_id)
        return group.member_ids if group else []

    # ── Model Assignment ──────────────────────────────────────────

    def assign_models(self, group_id, model_ids) -> bool:
        group = self.get(group_id)
        if not group:
            return False
        merged = list(set(group.allowed_model_ids + model_ids))
        self.update(group_id, allowed_model_ids=merged)
        return True

    def revoke_models(self, group_id, model_ids) -> bool:
        group = self.get(group_id)
        if not group:
            return False
        filtered = [m for m in group.allowed_model_ids if m not in model_ids]
        self.update(group_id, allowed_model_ids=filtered)
        return True

    def get_user_allowed_models(self, user_id) -> List[str]:
        models = set()
        for group in self.get_user_groups(user_id):
            models.update(group.allowed_model_ids)
        return list(models)

    # ── Agent Assignment ──────────────────────────────────────────

    def assign_agents(self, group_id, agent_ids) -> bool:
        group = self.get(group_id)
        if not group:
            return False
        merged = list(set(group.allowed_agent_ids + agent_ids))
        self.update(group_id, allowed_agent_ids=merged)
        return True

    def revoke_agents(self, group_id, agent_ids) -> bool:
        group = self.get(group_id)
        if not group:
            return False
        filtered = [a for a in group.allowed_agent_ids if a not in agent_ids]
        self.update(group_id, allowed_agent_ids=filtered)
        return True

    # ── Role Assignment ───────────────────────────────────────────

    def assign_roles(self, group_id, roles) -> bool:
        group = self.get(group_id)
        if not group:
            return False
        merged = list(set(group.assigned_roles + roles))
        self.update(group_id, assigned_roles=merged)
        return True

    # ── Queries ───────────────────────────────────────────────────

    def is_model_allowed(self, user_id, model_id) -> bool:
        allowed = self.get_user_allowed_models(user_id)
        return not allowed or model_id in allowed

    def get_groups_for_lob(self, lob) -> List[Group]:
        return [g for g in self.list_all() if g.lob.lower() == lob.lower()]

    def get_stats(self) -> Dict[str, Any]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_stats())
                if result:
                    return result
            except Exception:
                pass
        groups = list(self._groups.values())
        return {
            "total_groups": len(groups),
            "active_groups": sum(1 for g in groups if g.is_active),
            "total_members": sum(len(g.member_ids) for g in groups),
            "persistence": "in-memory",
        }
