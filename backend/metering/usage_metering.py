"""
Usage Metering — Cost tracking and aggregation per Group/LoB, Agent, Model, and Time.
Provides filterable reports for Dashboard and chargeback.

Phase 2: PostgreSQL-backed via async SQLAlchemy with in-memory fallback.
Real cost calculation from provider response metadata using a pricing table.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid
import logging

logger = logging.getLogger(__name__)


# ── Model Pricing Table (per 1K tokens) ──────────────────────────────────────

MODEL_PRICING: Dict[str, tuple] = {
    # Google Gemini
    "gemini-2.5-flash":         (0.00015, 0.0006),
    "gemini-2.5-pro":           (0.00125, 0.01),
    "gemini-2.0-flash":         (0.0001,  0.0004),
    "gemini-2.0-flash-lite":    (0.000075, 0.0003),
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


def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD from token counts using the pricing table."""
    # Sort keys longest-first so 'gpt-4o-mini' matches before 'gpt-4o'
    for key, (inp_cost, out_cost) in sorted(MODEL_PRICING.items(), key=lambda x: len(x[0]), reverse=True):
        if key in model_id:
            return round(
                (input_tokens / 1000.0) * inp_cost + (output_tokens / 1000.0) * out_cost,
                8,
            )
    return 0.0


class UsageRecord(BaseModel):
    """A single usage event."""
    record_id: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    group_id: str = ""
    lob: str = ""
    user_id: str = ""
    agent_id: str = ""
    model_id: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0
    latency_ms: float = 0
    status: str = "success"


class MeteringAggregation(BaseModel):
    """Aggregated usage stats."""
    dimension: str = ""  # "group", "lob", "agent", "model"
    dimension_value: str = ""
    total_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0
    avg_latency_ms: float = 0
    success_rate: float = 0
    input_tokens: int = 0
    output_tokens: int = 0


class UsageMeteringManager:
    """
    Tracks LLM usage and provides aggregations by group/LoB/agent/model/time.
    PostgreSQL-backed with in-memory fallback when DB is unavailable.
    """

    def __init__(self):
        self._records: List[UsageRecord] = []
        self._db_available = False

    def _get_session_factory(self):
        try:
            from backend.db.engine import get_session_factory
            return get_session_factory()
        except Exception:
            return None

    # ── Async DB helpers ──────────────────────────────────────────────

    async def _db_record(self, rec: UsageRecord) -> bool:
        factory = self._get_session_factory()
        if not factory:
            return False
        from backend.db.models import UsageRecordModel
        async with factory() as session:
            row = UsageRecordModel(
                id=rec.record_id, timestamp=rec.timestamp,
                group_id=rec.group_id, lob=rec.lob,
                user_id=rec.user_id, agent_id=rec.agent_id,
                model_id=rec.model_id, provider=rec.provider,
                input_tokens=rec.input_tokens, output_tokens=rec.output_tokens,
                total_tokens=rec.total_tokens, cost_usd=rec.cost_usd,
                latency_ms=rec.latency_ms, status=rec.status,
            )
            session.add(row)
            await session.commit()
            return True

    async def _db_filter_records(
        self,
        group_id: Optional[str] = None,
        lob: Optional[str] = None,
        agent_id: Optional[str] = None,
        model_id: Optional[str] = None,
        user_id: Optional[str] = None,
        period_days: int = 30,
    ) -> List[UsageRecord]:
        factory = self._get_session_factory()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import UsageRecordModel
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        async with factory() as session:
            q = select(UsageRecordModel).where(UsageRecordModel.timestamp >= cutoff)
            if group_id:
                q = q.where(UsageRecordModel.group_id == group_id)
            if lob:
                q = q.where(UsageRecordModel.lob == lob)
            if agent_id:
                q = q.where(UsageRecordModel.agent_id == agent_id)
            if model_id:
                q = q.where(UsageRecordModel.model_id == model_id)
            if user_id:
                q = q.where(UsageRecordModel.user_id == user_id)
            q = q.order_by(UsageRecordModel.timestamp.desc())
            rows = (await session.execute(q)).scalars().all()
            return [
                UsageRecord(
                    record_id=r.id, timestamp=r.timestamp,
                    group_id=r.group_id or "", lob=r.lob or "",
                    user_id=r.user_id or "", agent_id=r.agent_id or "",
                    model_id=r.model_id or "", provider=r.provider or "",
                    input_tokens=r.input_tokens, output_tokens=r.output_tokens,
                    total_tokens=r.total_tokens, cost_usd=r.cost_usd,
                    latency_ms=r.latency_ms, status=r.status or "success",
                )
                for r in rows
            ]

    async def _db_summary(self, group_id: Optional[str], lob: Optional[str],
                          agent_id: Optional[str], period_days: int) -> Dict[str, Any]:
        factory = self._get_session_factory()
        if not factory:
            return {}
        from sqlalchemy import select, func
        from backend.db.models import UsageRecordModel
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        async with factory() as session:
            q = select(
                func.count(UsageRecordModel.id).label("total"),
                func.sum(UsageRecordModel.total_tokens).label("tokens"),
                func.sum(UsageRecordModel.cost_usd).label("cost"),
                func.avg(UsageRecordModel.latency_ms).label("avg_lat"),
                func.count(UsageRecordModel.id).filter(UsageRecordModel.status == "success").label("success"),
            ).where(UsageRecordModel.timestamp >= cutoff)
            if group_id:
                q = q.where(UsageRecordModel.group_id == group_id)
            if lob:
                q = q.where(UsageRecordModel.lob == lob)
            if agent_id:
                q = q.where(UsageRecordModel.agent_id == agent_id)
            row = (await session.execute(q)).one()
            total = row.total or 0
            return {
                "period_days": period_days,
                "total_requests": total,
                "total_tokens": row.tokens or 0,
                "total_cost_usd": round(float(row.cost or 0), 6),
                "avg_latency_ms": round(float(row.avg_lat or 0), 1),
                "success_rate": round((row.success or 0) / max(total, 1) * 100, 1),
                "filters": {"group_id": group_id, "lob": lob, "agent_id": agent_id},
                "persistence": "postgresql",
            }

    async def _db_daily_trend(self, group_id: Optional[str], lob: Optional[str],
                              period_days: int) -> List[Dict[str, Any]]:
        factory = self._get_session_factory()
        if not factory:
            return []
        from sqlalchemy import select, func, cast, Date
        from backend.db.models import UsageRecordModel
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        async with factory() as session:
            day_col = cast(UsageRecordModel.timestamp, Date).label("day")
            q = (select(
                day_col,
                func.count(UsageRecordModel.id).label("requests"),
                func.sum(UsageRecordModel.total_tokens).label("tokens"),
                func.sum(UsageRecordModel.cost_usd).label("cost"),
            ).where(UsageRecordModel.timestamp >= cutoff)
             .group_by(day_col).order_by(day_col))
            if group_id:
                q = q.where(UsageRecordModel.group_id == group_id)
            if lob:
                q = q.where(UsageRecordModel.lob == lob)
            rows = (await session.execute(q)).all()
            return [
                {"date": str(r.day), "requests": r.requests,
                 "tokens": r.tokens or 0, "cost_usd": round(float(r.cost or 0), 6)}
                for r in rows
            ]

    # ── Sync-to-async bridge ──────────────────────────────────────────

    def _run_async(self, coro):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return asyncio.run(coro)

    # ── Public API ────────────────────────────────────────────────────

    def record(
        self,
        group_id: str = "",
        lob: str = "",
        user_id: str = "",
        agent_id: str = "",
        model_id: str = "",
        provider: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0,
        latency_ms: float = 0,
        status: str = "success",
    ) -> UsageRecord:
        # Auto-calculate cost from pricing table if not provided
        if cost_usd == 0 and model_id and (input_tokens > 0 or output_tokens > 0):
            cost_usd = calculate_cost(model_id, input_tokens, output_tokens)
        rec = UsageRecord(
            record_id=f"ur-{uuid.uuid4().hex[:10]}",
            group_id=group_id,
            lob=lob,
            user_id=user_id,
            agent_id=agent_id,
            model_id=model_id,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status=status,
        )
        # Persist to DB
        if self._db_available:
            try:
                self._run_async(self._db_record(rec))
            except Exception as e:
                logger.warning(f"[METERING] DB persist failed, kept in-memory: {e}")
                self._records.append(rec)
        else:
            self._records.append(rec)
        return rec

    def record_from_response(
        self,
        model_id: str,
        provider: str,
        llm_response: Any,
        agent_id: str = "",
        user_id: str = "",
        group_id: str = "",
        lob: str = "",
        latency_ms: float = 0,
    ) -> UsageRecord:
        """Extract real token counts from an LLM response and record usage."""
        input_tokens = 0
        output_tokens = 0
        # LangChain response metadata
        usage = getattr(llm_response, "usage_metadata", None)
        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
            output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
        # OpenAI-style response
        elif hasattr(llm_response, "usage"):
            u = llm_response.usage
            input_tokens = getattr(u, "prompt_tokens", 0)
            output_tokens = getattr(u, "completion_tokens", 0)
        return self.record(
            group_id=group_id, lob=lob, user_id=user_id,
            agent_id=agent_id, model_id=model_id, provider=provider,
            input_tokens=input_tokens, output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    def ingest_from_llm_log(self, log_entry, group_id: str = "", lob: str = ""):
        """Ingest a usage record from an LLMLogEntry."""
        self.record(
            group_id=group_id,
            lob=lob,
            user_id=getattr(log_entry, "user_id", ""),
            agent_id=getattr(log_entry, "agent_id", ""),
            model_id=getattr(log_entry, "model", ""),
            provider=getattr(log_entry, "provider", ""),
            input_tokens=getattr(log_entry, "prompt_tokens", 0),
            output_tokens=getattr(log_entry, "completion_tokens", 0),
            cost_usd=getattr(log_entry, "cost_usd", 0),
            latency_ms=getattr(log_entry, "latency_ms", 0),
            status=getattr(log_entry, "status", "success"),
        )

    def _filter_records(
        self,
        group_id: Optional[str] = None,
        lob: Optional[str] = None,
        agent_id: Optional[str] = None,
        model_id: Optional[str] = None,
        user_id: Optional[str] = None,
        period_days: int = 30,
    ) -> List[UsageRecord]:
        if self._db_available:
            return self._run_async(
                self._db_filter_records(group_id, lob, agent_id, model_id, user_id, period_days)
            )
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        filtered = []
        for r in self._records:
            ts = r.timestamp if r.timestamp.tzinfo else r.timestamp.replace(tzinfo=timezone.utc)
            if ts < cutoff:
                continue
            if group_id and r.group_id != group_id:
                continue
            if lob and r.lob != lob:
                continue
            if agent_id and r.agent_id != agent_id:
                continue
            if model_id and r.model_id != model_id:
                continue
            if user_id and r.user_id != user_id:
                continue
            filtered.append(r)
        return filtered

    def _aggregate(self, records: List[UsageRecord], dimension: str, dim_key_fn) -> List[MeteringAggregation]:
        buckets: Dict[str, List[UsageRecord]] = {}
        for r in records:
            key = dim_key_fn(r)
            if key not in buckets:
                buckets[key] = []
            buckets[key].append(r)

        results = []
        for key, recs in buckets.items():
            total = len(recs)
            success = sum(1 for r in recs if r.status == "success")
            results.append(MeteringAggregation(
                dimension=dimension,
                dimension_value=key,
                total_requests=total,
                total_tokens=sum(r.total_tokens for r in recs),
                total_cost_usd=round(sum(r.cost_usd for r in recs), 6),
                avg_latency_ms=round(sum(r.latency_ms for r in recs) / max(total, 1), 1),
                success_rate=round(success / max(total, 1) * 100, 1),
                input_tokens=sum(r.input_tokens for r in recs),
                output_tokens=sum(r.output_tokens for r in recs),
            ))
        return sorted(results, key=lambda a: a.total_cost_usd, reverse=True)

    # ── Public aggregation methods ────────────────────────────────

    def by_group(self, period_days: int = 30, **filters) -> List[MeteringAggregation]:
        records = self._filter_records(period_days=period_days, **filters)
        return self._aggregate(records, "group", lambda r: r.group_id or "unassigned")

    def by_lob(self, period_days: int = 30, **filters) -> List[MeteringAggregation]:
        records = self._filter_records(period_days=period_days, **filters)
        return self._aggregate(records, "lob", lambda r: r.lob or "unassigned")

    def by_agent(self, period_days: int = 30, **filters) -> List[MeteringAggregation]:
        records = self._filter_records(period_days=period_days, **filters)
        return self._aggregate(records, "agent", lambda r: r.agent_id or "unknown")

    def by_model(self, period_days: int = 30, **filters) -> List[MeteringAggregation]:
        records = self._filter_records(period_days=period_days, **filters)
        return self._aggregate(records, "model", lambda r: r.model_id or "unknown")

    def by_user(self, period_days: int = 30, **filters) -> List[MeteringAggregation]:
        records = self._filter_records(period_days=period_days, **filters)
        return self._aggregate(records, "user", lambda r: r.user_id or "unknown")

    def summary(
        self,
        group_id: Optional[str] = None,
        lob: Optional[str] = None,
        agent_id: Optional[str] = None,
        period_days: int = 30,
    ) -> Dict[str, Any]:
        if self._db_available:
            try:
                return self._run_async(self._db_summary(group_id, lob, agent_id, period_days))
            except Exception:
                pass
        records = self._filter_records(group_id=group_id, lob=lob, agent_id=agent_id, period_days=period_days)
        total = len(records)
        success = sum(1 for r in records if r.status == "success")
        return {
            "period_days": period_days,
            "total_requests": total,
            "total_tokens": sum(r.total_tokens for r in records),
            "total_cost_usd": round(sum(r.cost_usd for r in records), 6),
            "avg_latency_ms": round(sum(r.latency_ms for r in records) / max(total, 1), 1),
            "success_rate": round(success / max(total, 1) * 100, 1),
            "unique_agents": len(set(r.agent_id for r in records if r.agent_id)),
            "unique_models": len(set(r.model_id for r in records if r.model_id)),
            "unique_users": len(set(r.user_id for r in records if r.user_id)),
            "filters": {"group_id": group_id, "lob": lob, "agent_id": agent_id},
            "persistence": "in-memory",
        }

    def daily_trend(
        self,
        group_id: Optional[str] = None,
        lob: Optional[str] = None,
        period_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Cost trend aggregated by day."""
        if self._db_available:
            try:
                return self._run_async(self._db_daily_trend(group_id, lob, period_days))
            except Exception:
                pass
        records = self._filter_records(group_id=group_id, lob=lob, period_days=period_days)
        by_day: Dict[str, List[UsageRecord]] = {}
        for r in records:
            day = r.timestamp.strftime("%Y-%m-%d")
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(r)

        trend = []
        for day in sorted(by_day.keys()):
            recs = by_day[day]
            trend.append({
                "date": day,
                "requests": len(recs),
                "tokens": sum(r.total_tokens for r in recs),
                "cost_usd": round(sum(r.cost_usd for r in recs), 6),
            })
        return trend

    def export_billing(
        self,
        group_id: Optional[str] = None,
        lob: Optional[str] = None,
        period_days: int = 30,
    ) -> Dict[str, Any]:
        """Generate a billing export with breakdowns for chargeback."""
        records = self._filter_records(group_id=group_id, lob=lob, period_days=period_days)
        by_model = self._aggregate(records, "model", lambda r: r.model_id or "unknown")
        by_agent = self._aggregate(records, "agent", lambda r: r.agent_id or "unknown")
        total_cost = sum(r.cost_usd for r in records)
        return {
            "period_days": period_days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_cost_usd": round(total_cost, 6),
            "total_requests": len(records),
            "total_tokens": sum(r.total_tokens for r in records),
            "by_model": [m.model_dump() for m in by_model],
            "by_agent": [a.model_dump() for a in by_agent],
            "filters": {"group_id": group_id, "lob": lob},
        }
