"""
Guardrail Manager — Defines and enforces safety rules on agent inputs/outputs.
Rules can be scoped globally, per-group, or per-agent.
DB-backed with in-memory cache for fast reads.
"""

import uuid
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GuardrailScope(str, Enum):
    GLOBAL = "global"
    GROUP = "group"
    AGENT = "agent"


class GuardrailAction(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    REDACT = "redact"
    LOG = "log"


class GuardrailType(str, Enum):
    PII_DETECTION = "pii_detection"
    PROMPT_INJECTION = "prompt_injection"
    PROFANITY = "profanity"
    REGEX_MATCH = "regex_match"
    VALID_LENGTH = "valid_length"
    READING_TIME = "reading_time"
    CUSTOM = "custom"


class GuardrailRule(BaseModel):
    """A single guardrail rule definition (in-memory representation)."""
    rule_id: str = Field(default_factory=lambda: f"gr-{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    rule_type: GuardrailType = GuardrailType.CUSTOM
    scope: GuardrailScope = GuardrailScope.GLOBAL
    action: GuardrailAction = GuardrailAction.BLOCK
    enabled: bool = True

    # Scope binding
    agent_ids: List[str] = Field(default_factory=list)
    group_ids: List[str] = Field(default_factory=list)

    # Rule configuration
    applies_to: str = "both"  # "input", "output", "both"
    config: Dict[str, Any] = Field(default_factory=dict)

    # Guardrails AI service deployment state
    is_deployed: bool = False

    # Stats
    times_triggered: int = 0
    last_triggered: Optional[datetime] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "admin"

    class Config:
        use_enum_values = True


def _row_to_rule(row) -> GuardrailRule:
    """Convert a GuardrailRuleModel DB row to a GuardrailRule pydantic model."""
    return GuardrailRule(
        rule_id=row.id,
        name=row.name,
        description=row.description or "",
        rule_type=row.rule_type,
        scope=row.scope,
        action=row.action,
        enabled=row.enabled,
        agent_ids=row.agent_ids or [],
        group_ids=row.group_ids or [],
        applies_to=row.applies_to,
        config=row.config_json or {},
        is_deployed=row.is_deployed,
        times_triggered=row.times_triggered,
        last_triggered=row.last_triggered,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by or "admin",
    )


class GuardrailManager:
    """Manages guardrail rules with CRUD, scoping, and evaluation.
    Uses an in-memory cache for fast reads, writes through to PostgreSQL."""

    def __init__(self):
        self._rules: Dict[str, GuardrailRule] = {}
        self._db_available = False

    # ── DB Hydration ──────────────────────────────────────────────

    async def hydrate_from_db(self, session) -> int:
        """Load all guardrail rules from the DB into the in-memory cache."""
        from backend.db.models import GuardrailRuleModel
        from sqlalchemy import select
        result = await session.execute(select(GuardrailRuleModel))
        rows = result.scalars().all()
        self._rules.clear()
        for row in rows:
            rule = _row_to_rule(row)
            self._rules[rule.rule_id] = rule
        self._db_available = True
        logger.info(f"Hydrated {len(rows)} guardrail rules from DB")
        return len(rows)

    # ── DB Write-Through ──────────────────────────────────────────

    async def _get_session(self):
        from backend.db.engine import get_session_factory
        return get_session_factory()

    async def _db_create(self, rule: GuardrailRule):
        if not self._db_available:
            return
        try:
            from backend.db.models import GuardrailRuleModel
            factory = await self._get_session()
            async with factory() as session:
                row = GuardrailRuleModel(
                    id=rule.rule_id, name=rule.name, description=rule.description,
                    rule_type=rule.rule_type, scope=rule.scope, action=rule.action,
                    enabled=rule.enabled, applies_to=rule.applies_to,
                    config_json=rule.config, agent_ids=rule.agent_ids,
                    group_ids=rule.group_ids, is_deployed=rule.is_deployed,
                    times_triggered=rule.times_triggered, last_triggered=rule.last_triggered,
                    created_by=rule.created_by,
                )
                session.add(row)
                await session.commit()
        except Exception as e:
            logger.error(f"DB write failed (create {rule.rule_id}): {e}")

    async def _db_update(self, rule_id: str, updates: Dict[str, Any]):
        if not self._db_available:
            return
        try:
            from backend.db.models import GuardrailRuleModel
            from sqlalchemy import select
            factory = await self._get_session()
            async with factory() as session:
                result = await session.execute(
                    select(GuardrailRuleModel).where(GuardrailRuleModel.id == rule_id)
                )
                row = result.scalar_one_or_none()
                if row:
                    for k, v in updates.items():
                        db_col = "config_json" if k == "config" else k
                        if hasattr(row, db_col):
                            setattr(row, db_col, v)
                    row.updated_at = datetime.utcnow()
                    await session.commit()
        except Exception as e:
            logger.error(f"DB write failed (update {rule_id}): {e}")

    async def _db_delete(self, rule_id: str):
        if not self._db_available:
            return
        try:
            from backend.db.models import GuardrailRuleModel
            from sqlalchemy import select
            factory = await self._get_session()
            async with factory() as session:
                result = await session.execute(
                    select(GuardrailRuleModel).where(GuardrailRuleModel.id == rule_id)
                )
                row = result.scalar_one_or_none()
                if row:
                    await session.delete(row)
                    await session.commit()
        except Exception as e:
            logger.error(f"DB write failed (delete {rule_id}): {e}")

    # ── Sync CRUD (in-memory cache) ──────────────────────────────

    def create(
        self,
        name: str,
        description: str = "",
        rule_type: str = "custom",
        scope: str = "global",
        action: str = "block",
        applies_to: str = "both",
        config: Optional[Dict[str, Any]] = None,
        agent_ids: Optional[List[str]] = None,
        group_ids: Optional[List[str]] = None,
        created_by: str = "admin",
    ) -> GuardrailRule:
        rule = GuardrailRule(
            name=name,
            description=description,
            rule_type=GuardrailType(rule_type),
            scope=GuardrailScope(scope),
            action=GuardrailAction(action),
            applies_to=applies_to,
            config=config or {},
            agent_ids=agent_ids or [],
            group_ids=group_ids or [],
            created_by=created_by,
        )
        self._rules[rule.rule_id] = rule
        return rule

    def get(self, rule_id: str) -> Optional[GuardrailRule]:
        return self._rules.get(rule_id)

    def update(self, rule_id: str, updates: Dict[str, Any]) -> Optional[GuardrailRule]:
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        for k, v in updates.items():
            if hasattr(rule, k) and k not in ("rule_id", "created_at"):
                setattr(rule, k, v)
        rule.updated_at = datetime.utcnow()
        return rule

    def delete(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    # ── Async CRUD (cache + DB write-through) ─────────────────────

    async def create_async(self, **kwargs) -> GuardrailRule:
        rule = self.create(**kwargs)
        await self._db_create(rule)
        return rule

    async def update_async(self, rule_id: str, updates: Dict[str, Any]) -> Optional[GuardrailRule]:
        rule = self.update(rule_id, updates)
        if rule:
            await self._db_update(rule_id, updates)
        return rule

    async def delete_async(self, rule_id: str) -> bool:
        ok = self.delete(rule_id)
        if ok:
            await self._db_delete(rule_id)
        return ok

    # ── Read Helpers ──────────────────────────────────────────────

    def list_all(self) -> List[GuardrailRule]:
        return sorted(self._rules.values(), key=lambda r: r.created_at, reverse=True)

    def get_rules_for_agent(self, agent_id: str) -> List[GuardrailRule]:
        """Get all rules that apply to a specific agent (global + agent-scoped)."""
        return [
            r for r in self._rules.values()
            if r.enabled and (
                r.scope == "global"
                or (r.scope == "agent" and agent_id in r.agent_ids)
            )
        ]

    def get_rules_for_group(self, group_id: str) -> List[GuardrailRule]:
        """Get all rules that apply to a specific group."""
        return [
            r for r in self._rules.values()
            if r.enabled and (
                r.scope == "global"
                or (r.scope == "group" and group_id in r.group_ids)
            )
        ]

    def get_stats(self) -> Dict[str, Any]:
        rules = list(self._rules.values())
        by_type: Dict[str, int] = {}
        for r in rules:
            by_type[r.rule_type] = by_type.get(r.rule_type, 0) + 1
        return {
            "total_rules": len(rules),
            "enabled": sum(1 for r in rules if r.enabled),
            "disabled": sum(1 for r in rules if not r.enabled),
            "by_type": by_type,
            "total_triggers": sum(r.times_triggered for r in rules),
        }
