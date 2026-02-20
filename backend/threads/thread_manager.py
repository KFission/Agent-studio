"""
JAI Agent OS — Thread Manager
Manages conversation threads per agent, with message history,
checkpoints, and state persistence.

Phase 2: PostgreSQL-backed via async SQLAlchemy with in-memory fallback.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import hashlib
import time
import uuid
import logging

logger = logging.getLogger(__name__)


class ThreadStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    ERROR = "error"


class ThreadMessage(BaseModel):
    message_id: str = ""
    thread_id: str = ""
    role: str = "user"  # user, assistant, system, tool
    content: str = ""
    content_blocks: List[Dict] = Field(default_factory=list)
    tool_calls: List[Dict] = Field(default_factory=list)
    tool_call_id: str = ""
    name: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tokens: int = 0
    model: str = ""
    latency_ms: float = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThreadCheckpoint(BaseModel):
    checkpoint_id: str = ""
    thread_id: str = ""
    message_index: int = 0
    state: Dict[str, Any] = Field(default_factory=dict)
    parent_checkpoint_id: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Thread(BaseModel):
    thread_id: str = ""
    agent_id: str = ""
    tenant_id: str = "tenant-default"
    user_id: str = ""
    title: str = "New conversation"
    status: ThreadStatus = ThreadStatus.ACTIVE
    messages: List[ThreadMessage] = Field(default_factory=list)
    checkpoints: List[ThreadCheckpoint] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)
    interrupt: Optional[Dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Helper: Convert DB models ↔ Pydantic models ─────────────────────────────

def _thread_from_row(row) -> Thread:
    """Convert a ThreadModel ORM row to a Thread Pydantic model."""
    messages = []
    for m in (row.messages or []):
        messages.append(ThreadMessage(
            message_id=m.id,
            thread_id=m.thread_id,
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls_json or [],
            tool_call_id=m.tool_call_id or "",
            name=m.name or "",
            model=m.model or "",
            tokens=m.tokens or 0,
            latency_ms=m.latency_ms or 0,
            metadata=m.metadata_json or {},
            timestamp=m.created_at.replace(tzinfo=timezone.utc) if m.created_at else datetime.now(timezone.utc),
        ))
    return Thread(
        thread_id=row.id,
        agent_id=row.agent_id,
        tenant_id=row.tenant_id or "tenant-default",
        user_id=row.user_id or "",
        title=row.title or "New conversation",
        status=ThreadStatus(row.status) if row.status else ThreadStatus.ACTIVE,
        messages=messages,
        config=row.config_json or {},
        metadata=row.metadata_json or {},
        interrupt=row.interrupt_json,
        created_at=row.created_at.replace(tzinfo=timezone.utc) if row.created_at else datetime.now(timezone.utc),
        updated_at=row.updated_at.replace(tzinfo=timezone.utc) if row.updated_at else datetime.now(timezone.utc),
    )


class ThreadManager:
    """
    Manages conversation threads with full message history.
    PostgreSQL-backed with in-memory fallback when DB is unavailable.
    """

    def __init__(self):
        self._threads: Dict[str, Thread] = {}
        self._msg_count = 0
        self._db_available = False

    def _get_session_factory(self):
        try:
            from backend.db.engine import get_session_factory
            return get_session_factory()
        except Exception:
            return None

    # ── Async DB helpers ──────────────────────────────────────────────

    async def _db_create(self, agent_id: str, tenant_id: str, user_id: str,
                         title: str, config: Dict) -> Optional[Thread]:
        factory = self._get_session_factory()
        if not factory:
            return None
        from backend.db.models import ThreadModel
        tid = f"thread-{uuid.uuid4().hex[:10]}"
        async with factory() as session:
            row = ThreadModel(
                id=tid, agent_id=agent_id, tenant_id=tenant_id,
                user_id=user_id, title=title or "New conversation",
                status="active", config_json=config or {},
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _thread_from_row(row)

    async def _db_get(self, thread_id: str) -> Optional[Thread]:
        factory = self._get_session_factory()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import ThreadModel
        async with factory() as session:
            row = (await session.execute(
                select(ThreadModel).where(ThreadModel.id == thread_id)
            )).scalar_one_or_none()
            return _thread_from_row(row) if row else None

    async def _db_list(self, tenant_id: Optional[str], status: Optional[str],
                       limit: int) -> List[Thread]:
        factory = self._get_session_factory()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import ThreadModel
        async with factory() as session:
            q = select(ThreadModel)
            if tenant_id:
                q = q.where(ThreadModel.tenant_id == tenant_id)
            if status:
                q = q.where(ThreadModel.status == status)
            q = q.order_by(ThreadModel.updated_at.desc()).limit(limit)
            rows = (await session.execute(q)).scalars().all()
            return [_thread_from_row(r) for r in rows]

    async def _db_list_by_agent(self, agent_id: str, tenant_id: Optional[str],
                                limit: int) -> List[Thread]:
        factory = self._get_session_factory()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import ThreadModel
        async with factory() as session:
            q = select(ThreadModel).where(ThreadModel.agent_id == agent_id)
            if tenant_id:
                q = q.where(ThreadModel.tenant_id == tenant_id)
            q = q.order_by(ThreadModel.updated_at.desc()).limit(limit)
            rows = (await session.execute(q)).scalars().all()
            return [_thread_from_row(r) for r in rows]

    async def _db_add_message(self, thread_id: str, role: str, content: str,
                              tool_calls: List[Dict], tool_call_id: str,
                              name: str, model: str, latency_ms: float,
                              tokens: int, metadata: Dict) -> Optional[ThreadMessage]:
        factory = self._get_session_factory()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import ThreadModel, ThreadMessageModel
        async with factory() as session:
            thread_row = (await session.execute(
                select(ThreadModel).where(ThreadModel.id == thread_id)
            )).scalar_one_or_none()
            if not thread_row:
                return None
            msg_id = f"msg-{uuid.uuid4().hex[:8]}"
            msg_row = ThreadMessageModel(
                id=msg_id, thread_id=thread_id, role=role, content=content,
                tool_calls_json=tool_calls or [], tool_call_id=tool_call_id or "",
                name=name or "", model=model or "", tokens=tokens or 0,
                latency_ms=latency_ms or 0, metadata_json=metadata or {},
            )
            session.add(msg_row)
            # Auto-title from first user message
            if role == "user" and thread_row.title == "New conversation" and content:
                thread_row.title = content[:60] + ("..." if len(content) > 60 else "")
            thread_row.updated_at = datetime.utcnow()
            await session.commit()
            return ThreadMessage(
                message_id=msg_id, thread_id=thread_id, role=role,
                content=content, tool_calls=tool_calls or [],
                tool_call_id=tool_call_id or "", name=name or "",
                model=model or "", tokens=tokens or 0,
                latency_ms=latency_ms or 0, metadata=metadata or {},
            )

    async def _db_delete(self, thread_id: str) -> bool:
        factory = self._get_session_factory()
        if not factory:
            return False
        from sqlalchemy import select, delete as sa_delete
        from backend.db.models import ThreadModel
        async with factory() as session:
            row = (await session.execute(
                select(ThreadModel).where(ThreadModel.id == thread_id)
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def _db_update_status(self, thread_id: str, status: str) -> bool:
        factory = self._get_session_factory()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import ThreadModel
        async with factory() as session:
            row = (await session.execute(
                select(ThreadModel).where(ThreadModel.id == thread_id)
            )).scalar_one_or_none()
            if not row:
                return False
            row.status = status
            row.updated_at = datetime.utcnow()
            await session.commit()
            return True

    async def _db_set_interrupt(self, thread_id: str, interrupt: Dict) -> bool:
        factory = self._get_session_factory()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import ThreadModel
        async with factory() as session:
            row = (await session.execute(
                select(ThreadModel).where(ThreadModel.id == thread_id)
            )).scalar_one_or_none()
            if not row:
                return False
            row.interrupt_json = interrupt
            row.status = "interrupted"
            row.updated_at = datetime.utcnow()
            await session.commit()
            return True

    async def _db_resolve_interrupt(self, thread_id: str, action: str,
                                    response: Any = None) -> bool:
        factory = self._get_session_factory()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import ThreadModel
        async with factory() as session:
            row = (await session.execute(
                select(ThreadModel).where(ThreadModel.id == thread_id)
            )).scalar_one_or_none()
            if not row or not row.interrupt_json:
                return False
            row.interrupt_json["resolved"] = True
            row.interrupt_json["action"] = action
            row.interrupt_json["response"] = response
            row.interrupt_json["resolved_at"] = datetime.now(timezone.utc).isoformat()
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(row, "interrupt_json")
            row.status = "active"
            row.updated_at = datetime.utcnow()
            await session.commit()
            return True

    async def _db_get_messages(self, thread_id: str, limit: int,
                               offset: int) -> List[ThreadMessage]:
        factory = self._get_session_factory()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import ThreadMessageModel
        async with factory() as session:
            q = (select(ThreadMessageModel)
                 .where(ThreadMessageModel.thread_id == thread_id)
                 .order_by(ThreadMessageModel.created_at)
                 .offset(offset).limit(limit))
            rows = (await session.execute(q)).scalars().all()
            return [
                ThreadMessage(
                    message_id=m.id, thread_id=m.thread_id, role=m.role,
                    content=m.content, tool_calls=m.tool_calls_json or [],
                    tool_call_id=m.tool_call_id or "", name=m.name or "",
                    model=m.model or "", tokens=m.tokens or 0,
                    latency_ms=m.latency_ms or 0, metadata=m.metadata_json or {},
                    timestamp=m.created_at.replace(tzinfo=timezone.utc) if m.created_at else datetime.now(timezone.utc),
                )
                for m in rows
            ]

    async def _db_stats(self) -> Dict:
        factory = self._get_session_factory()
        if not factory:
            return {}
        from sqlalchemy import select, func
        from backend.db.models import ThreadModel, ThreadMessageModel
        async with factory() as session:
            total = (await session.execute(select(func.count(ThreadModel.id)))).scalar() or 0
            by_status = {}
            for s in ThreadStatus:
                cnt = (await session.execute(
                    select(func.count(ThreadModel.id)).where(ThreadModel.status == s.value)
                )).scalar() or 0
                by_status[s.value] = cnt
            total_msgs = (await session.execute(
                select(func.count(ThreadMessageModel.id))
            )).scalar() or 0
            return {
                "total_threads": total,
                "by_status": by_status,
                "total_messages": total_msgs,
                "persistence": "postgresql",
            }

    # ── Public sync API (delegates to DB or in-memory) ───────────────

    def create(self, agent_id: str, tenant_id: str = "tenant-default",
               user_id: str = "", title: str = "", config: Dict = None) -> Thread:
        if self._db_available:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                # We're inside an async context — use create_task workaround
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run,
                        self._db_create(agent_id, tenant_id, user_id, title, config)
                    ).result()
                if result:
                    return result
            else:
                result = asyncio.run(
                    self._db_create(agent_id, tenant_id, user_id, title, config)
                )
                if result:
                    return result
        # Fallback to in-memory
        tid = f"thread-{uuid.uuid4().hex[:10]}"
        thread = Thread(
            thread_id=tid, agent_id=agent_id, tenant_id=tenant_id,
            user_id=user_id, title=title or "New conversation",
            config=config or {},
        )
        self._threads[tid] = thread
        return thread

    def get(self, thread_id: str) -> Optional[Thread]:
        if self._db_available:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self._db_get(thread_id)).result()
                return result
            return asyncio.run(self._db_get(thread_id))
        return self._threads.get(thread_id)

    def list_by_agent(self, agent_id: str, tenant_id: Optional[str] = None,
                      limit: int = 50) -> List[Thread]:
        if self._db_available:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run,
                        self._db_list_by_agent(agent_id, tenant_id, limit)
                    ).result()
            return asyncio.run(self._db_list_by_agent(agent_id, tenant_id, limit))
        threads = [t for t in self._threads.values() if t.agent_id == agent_id]
        if tenant_id:
            threads = [t for t in threads if t.tenant_id == tenant_id]
        return sorted(threads, key=lambda t: t.updated_at, reverse=True)[:limit]

    def list_by_user(self, user_id: str, tenant_id: Optional[str] = None,
                     limit: int = 50) -> List[Thread]:
        threads = [t for t in self._threads.values() if t.user_id == user_id]
        if tenant_id:
            threads = [t for t in threads if t.tenant_id == tenant_id]
        return sorted(threads, key=lambda t: t.updated_at, reverse=True)[:limit]

    def list_all(self, tenant_id: Optional[str] = None, status: Optional[ThreadStatus] = None,
                 limit: int = 100) -> List[Thread]:
        if self._db_available:
            import asyncio
            s = status.value if status else None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run, self._db_list(tenant_id, s, limit)
                    ).result()
            return asyncio.run(self._db_list(tenant_id, s, limit))
        threads = list(self._threads.values())
        if tenant_id:
            threads = [t for t in threads if t.tenant_id == tenant_id]
        if status:
            threads = [t for t in threads if t.status == status]
        return sorted(threads, key=lambda t: t.updated_at, reverse=True)[:limit]

    def add_message(self, thread_id: str, role: str, content: str,
                    tool_calls: List[Dict] = None, tool_call_id: str = "",
                    name: str = "", model: str = "", latency_ms: float = 0,
                    tokens: int = 0, metadata: Dict = None) -> Optional[ThreadMessage]:
        if self._db_available:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run,
                        self._db_add_message(
                            thread_id, role, content, tool_calls or [],
                            tool_call_id, name, model, latency_ms, tokens,
                            metadata or {},
                        )
                    ).result()
            return asyncio.run(
                self._db_add_message(
                    thread_id, role, content, tool_calls or [],
                    tool_call_id, name, model, latency_ms, tokens,
                    metadata or {},
                )
            )
        # In-memory fallback
        thread = self._threads.get(thread_id)
        if not thread:
            return None
        self._msg_count += 1
        msg = ThreadMessage(
            message_id=f"msg-{uuid.uuid4().hex[:8]}",
            thread_id=thread_id, role=role, content=content,
            tool_calls=tool_calls or [], tool_call_id=tool_call_id,
            name=name, model=model, latency_ms=latency_ms,
            tokens=tokens, metadata=metadata or {},
        )
        thread.messages.append(msg)
        thread.updated_at = datetime.now(timezone.utc)
        # Auto-title from first user message
        if role == "user" and thread.title == "New conversation" and content:
            thread.title = content[:60] + ("..." if len(content) > 60 else "")
        return msg

    def get_messages(self, thread_id: str, limit: int = 100,
                     offset: int = 0) -> List[ThreadMessage]:
        if self._db_available:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run,
                        self._db_get_messages(thread_id, limit, offset)
                    ).result()
            return asyncio.run(self._db_get_messages(thread_id, limit, offset))
        thread = self._threads.get(thread_id)
        if not thread:
            return []
        return thread.messages[offset:offset + limit]

    def create_checkpoint(self, thread_id: str, state: Dict = None) -> Optional[ThreadCheckpoint]:
        thread = self.get(thread_id)
        if not thread:
            return None
        cp = ThreadCheckpoint(
            checkpoint_id=f"cp-{uuid.uuid4().hex[:8]}",
            thread_id=thread_id,
            message_index=len(thread.messages),
            state=state or {},
            parent_checkpoint_id=thread.checkpoints[-1].checkpoint_id if thread.checkpoints else "",
        )
        thread.checkpoints.append(cp)
        return cp

    def set_interrupt(self, thread_id: str, interrupt: Dict) -> bool:
        if self._db_available:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run, self._db_set_interrupt(thread_id, interrupt)
                    ).result()
            return asyncio.run(self._db_set_interrupt(thread_id, interrupt))
        thread = self._threads.get(thread_id)
        if not thread:
            return False
        thread.interrupt = interrupt
        thread.status = ThreadStatus.INTERRUPTED
        thread.updated_at = datetime.now(timezone.utc)
        return True

    def resolve_interrupt(self, thread_id: str, action: str, response: Any = None) -> bool:
        if self._db_available:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run,
                        self._db_resolve_interrupt(thread_id, action, response)
                    ).result()
            return asyncio.run(self._db_resolve_interrupt(thread_id, action, response))
        thread = self._threads.get(thread_id)
        if not thread or not thread.interrupt:
            return False
        thread.interrupt["resolved"] = True
        thread.interrupt["action"] = action
        thread.interrupt["response"] = response
        thread.interrupt["resolved_at"] = datetime.now(timezone.utc).isoformat()
        thread.status = ThreadStatus.ACTIVE
        thread.updated_at = datetime.now(timezone.utc)
        return True

    def update_status(self, thread_id: str, status: ThreadStatus) -> bool:
        if self._db_available:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run,
                        self._db_update_status(thread_id, status.value)
                    ).result()
            return asyncio.run(self._db_update_status(thread_id, status.value))
        thread = self._threads.get(thread_id)
        if not thread:
            return False
        thread.status = status
        thread.updated_at = datetime.now(timezone.utc)
        return True

    def delete(self, thread_id: str) -> bool:
        if self._db_available:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run, self._db_delete(thread_id)
                    ).result()
            return asyncio.run(self._db_delete(thread_id))
        return self._threads.pop(thread_id, None) is not None

    def get_stats(self) -> Dict:
        if self._db_available:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self._db_stats()).result()
                if result:
                    return result
            else:
                result = asyncio.run(self._db_stats())
                if result:
                    return result
        threads = list(self._threads.values())
        return {
            "total_threads": len(threads),
            "by_status": {s.value: sum(1 for t in threads if t.status == s) for s in ThreadStatus},
            "total_messages": sum(len(t.messages) for t in threads),
            "interrupted": sum(1 for t in threads if t.interrupt and not t.interrupt.get("resolved")),
            "persistence": "in-memory",
        }
