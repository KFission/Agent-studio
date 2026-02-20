"""
Agent Memory Manager — Short-term and long-term memory per agent.
Short-term: conversation buffer (last N messages).
Long-term: summarized knowledge persisted across sessions.
PostgreSQL-backed with in-memory fallback.
"""

import uuid
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class MemoryEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    memory_type: MemoryType
    agent_id: str
    session_id: str = "default"
    role: str = "user"  # user, assistant, system, tool
    content: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    token_count: int = 0


class MemorySummary(BaseModel):
    agent_id: str
    session_id: str
    summary: str
    message_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


def _mem_from_row(row) -> MemoryEntry:
    return MemoryEntry(
        entry_id=row.id, memory_type=MemoryType(row.memory_type),
        agent_id=row.agent_id, session_id=row.session_id or "default",
        role=row.role or "user", content=row.content or "",
        metadata=row.metadata_json if isinstance(row.metadata_json, dict) else {},
        timestamp=row.created_at or datetime.utcnow(),
        token_count=row.token_count or 0,
    )


class AgentMemoryManager:
    """
    Manages per-agent short-term and long-term memory.
    PostgreSQL-backed with in-memory fallback.
    """

    def __init__(self):
        self._short_term: Dict[str, List[MemoryEntry]] = {}
        self._long_term: Dict[str, List[MemoryEntry]] = {}
        self._summaries: Dict[str, List[MemorySummary]] = {}
        self._db_available = False

    def _sf(self):
        from backend.db.sync_bridge import get_session_factory
        return get_session_factory()

    def _st_key(self, agent_id: str, session_id: str) -> str:
        return f"{agent_id}:{session_id}"

    # ── Async DB helpers ──────────────────────────────────────────

    async def _db_add(self, entry: MemoryEntry) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from backend.db.models import MemoryEntryModel
        async with factory() as session:
            row = MemoryEntryModel(
                id=entry.entry_id, memory_type=entry.memory_type.value,
                agent_id=entry.agent_id, session_id=entry.session_id,
                role=entry.role, content=entry.content,
                token_count=entry.token_count, metadata_json=entry.metadata,
            )
            session.add(row)
            await session.commit()
            return True

    async def _db_get_conversation(self, agent_id, session_id, limit) -> List[MemoryEntry]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import MemoryEntryModel
        async with factory() as session:
            q = (select(MemoryEntryModel)
                 .where(MemoryEntryModel.agent_id == agent_id)
                 .where(MemoryEntryModel.session_id == session_id)
                 .where(MemoryEntryModel.memory_type == "short_term")
                 .order_by(MemoryEntryModel.created_at.desc())
                 .limit(limit))
            rows = (await session.execute(q)).scalars().all()
            return [_mem_from_row(r) for r in reversed(rows)]

    async def _db_get_long_term(self, agent_id, limit) -> List[MemoryEntry]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import MemoryEntryModel
        async with factory() as session:
            q = (select(MemoryEntryModel)
                 .where(MemoryEntryModel.agent_id == agent_id)
                 .where(MemoryEntryModel.memory_type == "long_term")
                 .order_by(MemoryEntryModel.created_at.desc())
                 .limit(limit))
            rows = (await session.execute(q)).scalars().all()
            return [_mem_from_row(r) for r in reversed(rows)]

    async def _db_delete_entry(self, entry_id) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import MemoryEntryModel
        async with factory() as session:
            row = (await session.execute(
                select(MemoryEntryModel).where(MemoryEntryModel.id == entry_id)
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def _db_clear_session(self, agent_id, session_id) -> int:
        factory = self._sf()
        if not factory:
            return 0
        from sqlalchemy import delete as sa_delete, select, func
        from backend.db.models import MemoryEntryModel
        async with factory() as session:
            count = (await session.execute(
                select(func.count(MemoryEntryModel.id))
                .where(MemoryEntryModel.agent_id == agent_id)
                .where(MemoryEntryModel.session_id == session_id)
                .where(MemoryEntryModel.memory_type == "short_term")
            )).scalar() or 0
            await session.execute(
                sa_delete(MemoryEntryModel)
                .where(MemoryEntryModel.agent_id == agent_id)
                .where(MemoryEntryModel.session_id == session_id)
                .where(MemoryEntryModel.memory_type == "short_term")
            )
            await session.commit()
            return count

    async def _db_clear_all(self, agent_id) -> Dict[str, int]:
        factory = self._sf()
        if not factory:
            return {"short_term_cleared": 0, "long_term_cleared": 0}
        from sqlalchemy import delete as sa_delete, select, func
        from backend.db.models import MemoryEntryModel
        async with factory() as session:
            st = (await session.execute(
                select(func.count(MemoryEntryModel.id))
                .where(MemoryEntryModel.agent_id == agent_id)
                .where(MemoryEntryModel.memory_type == "short_term")
            )).scalar() or 0
            lt = (await session.execute(
                select(func.count(MemoryEntryModel.id))
                .where(MemoryEntryModel.agent_id == agent_id)
                .where(MemoryEntryModel.memory_type == "long_term")
            )).scalar() or 0
            await session.execute(
                sa_delete(MemoryEntryModel).where(MemoryEntryModel.agent_id == agent_id)
            )
            await session.commit()
            return {"short_term_cleared": st, "long_term_cleared": lt}

    # ── Short-Term Memory ─────────────────────────────────────────

    def add_message(
        self, agent_id: str, session_id: str, role: str, content: str,
        metadata: Optional[Dict[str, Any]] = None, max_messages: int = 50,
    ) -> MemoryEntry:
        key = self._st_key(agent_id, session_id)
        entry = MemoryEntry(
            memory_type=MemoryType.SHORT_TERM,
            agent_id=agent_id, session_id=session_id,
            role=role, content=content,
            metadata=metadata or {}, token_count=len(content) // 4,
        )
        if key not in self._short_term:
            self._short_term[key] = []
        self._short_term[key].append(entry)
        if len(self._short_term[key]) > max_messages:
            self._short_term[key] = self._short_term[key][-max_messages:]
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_add(entry))
            except Exception:
                pass
        return entry

    def get_conversation(self, agent_id: str, session_id: str, limit: int = 50) -> List[MemoryEntry]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_get_conversation(agent_id, session_id, limit))
            except Exception:
                pass
        key = self._st_key(agent_id, session_id)
        return self._short_term.get(key, [])[-limit:]

    def clear_session(self, agent_id: str, session_id: str) -> int:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                count = run_async(self._db_clear_session(agent_id, session_id))
                self._short_term.pop(self._st_key(agent_id, session_id), None)
                return count
            except Exception:
                pass
        key = self._st_key(agent_id, session_id)
        count = len(self._short_term.get(key, []))
        self._short_term.pop(key, None)
        return count

    def list_sessions(self, agent_id: str) -> List[Dict[str, Any]]:
        sessions = []
        prefix = f"{agent_id}:"
        for key, entries in self._short_term.items():
            if key.startswith(prefix):
                sid = key[len(prefix):]
                sessions.append({
                    "session_id": sid,
                    "message_count": len(entries),
                    "last_message": entries[-1].timestamp.isoformat() if entries else None,
                })
        return sessions

    # ── Long-Term Memory ──────────────────────────────────────────

    def store_long_term(
        self, agent_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        entry = MemoryEntry(
            memory_type=MemoryType.LONG_TERM,
            agent_id=agent_id, role="system",
            content=content, metadata=metadata or {},
            token_count=len(content) // 4,
        )
        if agent_id not in self._long_term:
            self._long_term[agent_id] = []
        self._long_term[agent_id].append(entry)
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_add(entry))
            except Exception:
                pass
        return entry

    def get_long_term(self, agent_id: str, limit: int = 20) -> List[MemoryEntry]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_get_long_term(agent_id, limit))
            except Exception:
                pass
        return self._long_term.get(agent_id, [])[-limit:]

    def search_long_term(self, agent_id: str, query: str) -> List[MemoryEntry]:
        q = query.lower()
        entries = self.get_long_term(agent_id, limit=1000)
        return [e for e in entries if q in e.content.lower()]

    def delete_long_term(self, agent_id: str, entry_id: str) -> bool:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_delete_entry(entry_id))
            except Exception:
                pass
        entries = self._long_term.get(agent_id, [])
        for i, e in enumerate(entries):
            if e.entry_id == entry_id:
                entries.pop(i)
                return True
        return False

    # ── Summarization ─────────────────────────────────────────────

    def create_summary(self, agent_id: str, session_id: str, summary_text: str) -> MemorySummary:
        key = self._st_key(agent_id, session_id)
        msg_count = len(self._short_term.get(key, []))
        s = MemorySummary(
            agent_id=agent_id, session_id=session_id,
            summary=summary_text, message_count=msg_count,
        )
        if agent_id not in self._summaries:
            self._summaries[agent_id] = []
        self._summaries[agent_id].append(s)
        self.store_long_term(agent_id, f"[Session Summary] {summary_text}", {"session_id": session_id})
        return s

    def get_summaries(self, agent_id: str) -> List[MemorySummary]:
        return self._summaries.get(agent_id, [])

    # ── Stats ─────────────────────────────────────────────────────

    def get_agent_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        st_count = sum(
            len(v) for k, v in self._short_term.items() if k.startswith(f"{agent_id}:")
        )
        lt_count = len(self._long_term.get(agent_id, []))
        sessions = self.list_sessions(agent_id)
        return {
            "agent_id": agent_id,
            "short_term_messages": st_count,
            "long_term_entries": lt_count,
            "active_sessions": len(sessions),
            "summaries": len(self._summaries.get(agent_id, [])),
        }

    def clear_all(self, agent_id: str) -> Dict[str, int]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_clear_all(agent_id))
                for k in list(self._short_term.keys()):
                    if k.startswith(f"{agent_id}:"):
                        del self._short_term[k]
                self._long_term.pop(agent_id, None)
                self._summaries.pop(agent_id, None)
                return result
            except Exception:
                pass
        st = sum(len(v) for k, v in list(self._short_term.items()) if k.startswith(f"{agent_id}:"))
        lt = len(self._long_term.get(agent_id, []))
        for k in list(self._short_term.keys()):
            if k.startswith(f"{agent_id}:"):
                del self._short_term[k]
        self._long_term.pop(agent_id, None)
        self._summaries.pop(agent_id, None)
        return {"short_term_cleared": st, "long_term_cleared": lt}
