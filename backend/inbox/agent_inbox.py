"""
JAI Agent OS — Agent Inbox
Human-in-the-loop interrupt handling, approval workflows, and thread state management.
Mirrors OAP's agent-inbox component with approve/reject/edit actions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import hashlib
import time


class InboxStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class InboxAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    ESCALATE = "escalate"
    DEFER = "defer"


class InterruptValue(BaseModel):
    type: str = "generic"  # generic, tool_call, approval, review, escalation
    title: str = ""
    description: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    tool_calls: List[Dict] = Field(default_factory=list)
    required_role: str = ""
    sla_minutes: int = 0


class InboxItem(BaseModel):
    item_id: str = ""
    thread_id: str = ""
    agent_id: str = ""
    tenant_id: str = "tenant-default"
    user_id: str = ""
    status: InboxStatus = InboxStatus.PENDING
    interrupt: InterruptValue = Field(default_factory=InterruptValue)
    # Thread context
    thread_title: str = ""
    message_count: int = 0
    last_message_preview: str = ""
    # Resolution
    action: Optional[InboxAction] = None
    response: Optional[Any] = None
    resolved_by: str = ""
    resolved_at: Optional[datetime] = None
    # Metadata
    priority: int = 0  # 0=normal, 1=high, 2=urgent
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _inbox_from_row(row) -> InboxItem:
    interrupt_data = row.interrupt_json if isinstance(row.interrupt_json, dict) else {}
    return InboxItem(
        item_id=row.id, thread_id=row.thread_id or "", agent_id=row.agent_id or "",
        tenant_id=row.tenant_id or "tenant-default", user_id=row.user_id or "",
        status=InboxStatus(row.status) if row.status else InboxStatus.PENDING,
        interrupt=InterruptValue(**interrupt_data) if interrupt_data else InterruptValue(),
        thread_title=row.thread_title or "", message_count=row.message_count or 0,
        last_message_preview=row.last_message_preview or "",
        action=InboxAction(row.action) if row.action else None,
        response=row.response_json,
        resolved_by=row.resolved_by or "", resolved_at=row.resolved_at,
        priority=row.priority or 0,
        tags=row.tags if isinstance(row.tags, list) else [],
        metadata=row.metadata_json if isinstance(row.metadata_json, dict) else {},
        created_at=row.created_at or datetime.now(timezone.utc),
        updated_at=row.updated_at or datetime.now(timezone.utc),
    )


class AgentInbox:
    """
    Manages human-in-the-loop interrupts across all agents.
    PostgreSQL-backed with in-memory fallback.
    """

    def __init__(self):
        self._items: Dict[str, InboxItem] = {}
        self._count = 0
        self._db_available = False

    def _sf(self):
        from backend.db.sync_bridge import get_session_factory
        return get_session_factory()

    # ── Async DB helpers ──────────────────────────────────────────

    async def _db_create(self, item: InboxItem) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from backend.db.models import InboxItemModel
        async with factory() as session:
            row = InboxItemModel(
                id=item.item_id, thread_id=item.thread_id, agent_id=item.agent_id,
                tenant_id=item.tenant_id, user_id=item.user_id,
                status=item.status.value,
                interrupt_json=item.interrupt.model_dump() if item.interrupt else {},
                thread_title=item.thread_title, message_count=item.message_count,
                last_message_preview=item.last_message_preview,
                priority=item.priority, tags=item.tags,
                metadata_json=item.metadata,
            )
            session.add(row)
            await session.commit()
            return True

    async def _db_get(self, item_id) -> Optional[InboxItem]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import InboxItemModel
        async with factory() as session:
            row = (await session.execute(
                select(InboxItemModel).where(InboxItemModel.id == item_id)
            )).scalar_one_or_none()
            return _inbox_from_row(row) if row else None

    async def _db_resolve(self, item_id, action, response, resolved_by) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import InboxItemModel
        status_map = {
            InboxAction.APPROVE: InboxStatus.APPROVED,
            InboxAction.REJECT: InboxStatus.REJECTED,
            InboxAction.EDIT: InboxStatus.EDITED,
            InboxAction.ESCALATE: InboxStatus.PENDING,
            InboxAction.DEFER: InboxStatus.PENDING,
        }
        async with factory() as session:
            row = (await session.execute(
                select(InboxItemModel).where(InboxItemModel.id == item_id)
            )).scalar_one_or_none()
            if not row or row.status != "pending":
                return False
            row.status = status_map.get(action, InboxStatus.APPROVED).value
            row.action = action.value
            row.response_json = response
            row.resolved_by = resolved_by
            row.resolved_at = datetime.now(timezone.utc)
            row.updated_at = datetime.now(timezone.utc)
            await session.commit()
            return True

    async def _db_list(self, tenant_id=None, agent_id=None, status=None,
                       user_id=None, limit=50, offset=0) -> List[InboxItem]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import InboxItemModel
        async with factory() as session:
            q = select(InboxItemModel)
            if tenant_id:
                q = q.where(InboxItemModel.tenant_id == tenant_id)
            if agent_id:
                q = q.where(InboxItemModel.agent_id == agent_id)
            if status:
                q = q.where(InboxItemModel.status == status.value)
            if user_id:
                q = q.where(InboxItemModel.user_id == user_id)
            q = q.order_by(InboxItemModel.priority.desc(), InboxItemModel.created_at.desc())
            q = q.offset(offset).limit(limit)
            rows = (await session.execute(q)).scalars().all()
            return [_inbox_from_row(r) for r in rows]

    async def _db_count_pending(self, tenant_id=None, agent_id=None) -> int:
        factory = self._sf()
        if not factory:
            return 0
        from sqlalchemy import select, func
        from backend.db.models import InboxItemModel
        async with factory() as session:
            q = select(func.count(InboxItemModel.id)).where(InboxItemModel.status == "pending")
            if tenant_id:
                q = q.where(InboxItemModel.tenant_id == tenant_id)
            if agent_id:
                q = q.where(InboxItemModel.agent_id == agent_id)
            return (await session.execute(q)).scalar() or 0

    async def _db_delete(self, item_id) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import InboxItemModel
        async with factory() as session:
            row = (await session.execute(
                select(InboxItemModel).where(InboxItemModel.id == item_id)
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
        from backend.db.models import InboxItemModel
        async with factory() as session:
            total = (await session.execute(select(func.count(InboxItemModel.id)))).scalar() or 0
            pending = (await session.execute(
                select(func.count(InboxItemModel.id)).where(InboxItemModel.status == "pending")
            )).scalar() or 0
            return {"total": total, "pending": pending, "persistence": "postgresql"}

    # ── Public sync API ───────────────────────────────────────────

    def create(self, thread_id: str, agent_id: str, interrupt: InterruptValue,
               tenant_id: str = "tenant-default", user_id: str = "",
               thread_title: str = "", message_count: int = 0,
               last_message_preview: str = "", priority: int = 0,
               tags: List[str] = None) -> InboxItem:
        self._count += 1
        iid = f"inbox-{hashlib.md5(f'{self._count}-{time.time()}'.encode()).hexdigest()[:8]}"
        item = InboxItem(
            item_id=iid, thread_id=thread_id, agent_id=agent_id,
            tenant_id=tenant_id, user_id=user_id,
            interrupt=interrupt, thread_title=thread_title,
            message_count=message_count, last_message_preview=last_message_preview,
            priority=priority, tags=tags or [],
        )
        self._items[iid] = item
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_create(item))
            except Exception:
                pass
        return item

    def get(self, item_id: str) -> Optional[InboxItem]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_get(item_id))
                if result:
                    return result
            except Exception:
                pass
        return self._items.get(item_id)

    def resolve(self, item_id: str, action: InboxAction, response: Any = None,
                resolved_by: str = "") -> Optional[InboxItem]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                ok = run_async(self._db_resolve(item_id, action, response, resolved_by))
                if ok:
                    # Also update in-memory
                    item = self._items.get(item_id)
                    if item:
                        status_map = {
                            InboxAction.APPROVE: InboxStatus.APPROVED,
                            InboxAction.REJECT: InboxStatus.REJECTED,
                            InboxAction.EDIT: InboxStatus.EDITED,
                            InboxAction.ESCALATE: InboxStatus.PENDING,
                            InboxAction.DEFER: InboxStatus.PENDING,
                        }
                        item.status = status_map.get(action, InboxStatus.APPROVED)
                        item.action = action
                        item.response = response
                        item.resolved_by = resolved_by
                        item.resolved_at = datetime.now(timezone.utc)
                    return item or self.get(item_id)
            except Exception:
                pass
        # In-memory fallback
        item = self._items.get(item_id)
        if not item or item.status != InboxStatus.PENDING:
            return None
        status_map = {
            InboxAction.APPROVE: InboxStatus.APPROVED,
            InboxAction.REJECT: InboxStatus.REJECTED,
            InboxAction.EDIT: InboxStatus.EDITED,
            InboxAction.ESCALATE: InboxStatus.PENDING,
            InboxAction.DEFER: InboxStatus.PENDING,
        }
        item.status = status_map.get(action, InboxStatus.APPROVED)
        item.action = action
        item.response = response
        item.resolved_by = resolved_by
        item.resolved_at = datetime.now(timezone.utc)
        item.updated_at = datetime.now(timezone.utc)
        return item

    def list_items(self, tenant_id: Optional[str] = None, agent_id: Optional[str] = None,
                   status: Optional[InboxStatus] = None, user_id: Optional[str] = None,
                   limit: int = 50, offset: int = 0) -> List[InboxItem]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_list(tenant_id, agent_id, status, user_id, limit, offset))
            except Exception:
                pass
        items = list(self._items.values())
        if tenant_id:
            items = [i for i in items if i.tenant_id == tenant_id]
        if agent_id:
            items = [i for i in items if i.agent_id == agent_id]
        if status:
            items = [i for i in items if i.status == status]
        if user_id:
            items = [i for i in items if i.user_id == user_id]
        items.sort(key=lambda i: (i.priority, i.created_at), reverse=True)
        return items[offset:offset + limit]

    def count_pending(self, tenant_id: Optional[str] = None,
                      agent_id: Optional[str] = None) -> int:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_count_pending(tenant_id, agent_id))
            except Exception:
                pass
        items = [i for i in self._items.values() if i.status == InboxStatus.PENDING]
        if tenant_id:
            items = [i for i in items if i.tenant_id == tenant_id]
        if agent_id:
            items = [i for i in items if i.agent_id == agent_id]
        return len(items)

    def bulk_resolve(self, item_ids: List[str], action: InboxAction,
                     resolved_by: str = "") -> int:
        count = 0
        for iid in item_ids:
            if self.resolve(iid, action, resolved_by=resolved_by):
                count += 1
        return count

    def delete(self, item_id: str) -> bool:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_delete(item_id))
            except Exception:
                pass
        return self._items.pop(item_id, None) is not None

    def get_stats(self) -> Dict:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_stats())
                if result:
                    return result
            except Exception:
                pass
        items = list(self._items.values())
        return {
            "total": len(items),
            "by_status": {s.value: sum(1 for i in items if i.status == s) for s in InboxStatus},
            "pending": sum(1 for i in items if i.status == InboxStatus.PENDING),
            "avg_resolution_time_minutes": self._avg_resolution_time(items),
            "persistence": "in-memory",
        }

    def _avg_resolution_time(self, items: List[InboxItem]) -> float:
        resolved = [i for i in items if i.resolved_at]
        if not resolved:
            return 0
        total = sum((i.resolved_at - i.created_at).total_seconds() / 60 for i in resolved)
        return round(total / len(resolved), 1)
