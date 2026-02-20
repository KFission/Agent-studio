"""
JAI Agent OS — LLM Observability & Diagnostics
Captures every LLM request/response with latency, tokens, cost, errors.
Integrates with LangSmith for production tracing.
Provides diagnostic views for debugging agent behavior.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import hashlib
import time


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LLMLogEntry(BaseModel):
    log_id: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: LogLevel = LogLevel.INFO
    # Request context
    tenant_id: str = ""
    user_id: str = ""
    agent_id: str = ""
    thread_id: str = ""
    request_id: str = ""
    # LLM details
    provider: str = ""
    model: str = ""
    prompt: str = ""
    prompt_tokens: int = 0
    response: str = ""
    completion_tokens: int = 0
    total_tokens: int = 0
    # Performance
    latency_ms: float = 0
    time_to_first_token_ms: float = 0
    tokens_per_second: float = 0
    # Cost
    cost_usd: float = 0
    # Status
    status: str = "success"
    error_message: str = ""
    error_type: str = ""
    # Tool calls
    tool_calls: List[Dict] = Field(default_factory=list)
    tool_results: List[Dict] = Field(default_factory=list)
    # Metadata
    temperature: float = 0
    max_tokens: int = 0
    stop_reason: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Trace
    langsmith_run_id: str = ""
    langsmith_trace_url: str = ""
    parent_run_id: str = ""
    tags: List[str] = Field(default_factory=list)


class DiagnosticSummary(BaseModel):
    period: str = "last_hour"
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    error_rate: float = 0
    avg_latency_ms: float = 0
    p50_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    total_tokens: int = 0
    total_cost_usd: float = 0
    avg_tokens_per_request: float = 0
    requests_per_minute: float = 0
    by_model: Dict[str, Dict] = Field(default_factory=dict)
    by_provider: Dict[str, Dict] = Field(default_factory=dict)
    by_agent: Dict[str, Dict] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)
    top_errors: List[Dict] = Field(default_factory=list)


class LLMLogManager:
    """
    Central observability hub for all LLM interactions.
    Stores logs in-memory (Phase 1), with hooks for LangSmith and external sinks.
    """

    def __init__(self, max_entries: int = 50000):
        self._logs: List[LLMLogEntry] = []
        self._max_entries = max_entries
        self._log_count = 0

    def log(self, entry: LLMLogEntry) -> str:
        self._log_count += 1
        if not entry.log_id:
            entry.log_id = f"log-{hashlib.md5(f'{self._log_count}-{time.time()}'.encode()).hexdigest()[:10]}"
        if entry.latency_ms > 0 and entry.completion_tokens > 0:
            entry.tokens_per_second = round(entry.completion_tokens / (entry.latency_ms / 1000), 1)
        self._logs.append(entry)
        if len(self._logs) > self._max_entries:
            self._logs = self._logs[-self._max_entries // 2:]
        return entry.log_id

    def log_request(self, tenant_id: str, agent_id: str, model: str, provider: str,
                    prompt: str, response: str, prompt_tokens: int, completion_tokens: int,
                    latency_ms: float, cost_usd: float, status: str = "success",
                    error_message: str = "", thread_id: str = "", user_id: str = "",
                    tool_calls: List[Dict] = None, metadata: Dict = None,
                    langsmith_run_id: str = "", tags: List[str] = None) -> str:
        entry = LLMLogEntry(
            tenant_id=tenant_id, agent_id=agent_id, model=model, provider=provider,
            prompt=prompt[:500], response=response[:500],
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms, cost_usd=cost_usd, status=status,
            error_message=error_message, thread_id=thread_id, user_id=user_id,
            tool_calls=tool_calls or [], metadata=metadata or {},
            langsmith_run_id=langsmith_run_id, tags=tags or [],
        )
        return self.log(entry)

    def get_log(self, log_id: str) -> Optional[LLMLogEntry]:
        for log in reversed(self._logs):
            if log.log_id == log_id:
                return log
        return None

    def query(self, tenant_id: Optional[str] = None, agent_id: Optional[str] = None,
              model: Optional[str] = None, provider: Optional[str] = None,
              status: Optional[str] = None, level: Optional[LogLevel] = None,
              thread_id: Optional[str] = None, limit: int = 100,
              offset: int = 0) -> List[LLMLogEntry]:
        logs = self._logs
        if tenant_id:
            logs = [l for l in logs if l.tenant_id == tenant_id]
        if agent_id:
            logs = [l for l in logs if l.agent_id == agent_id]
        if model:
            logs = [l for l in logs if l.model == model]
        if provider:
            logs = [l for l in logs if l.provider == provider]
        if status:
            logs = [l for l in logs if l.status == status]
        if level:
            logs = [l for l in logs if l.level == level]
        if thread_id:
            logs = [l for l in logs if l.thread_id == thread_id]
        return sorted(logs, key=lambda l: l.timestamp, reverse=True)[offset:offset + limit]

    def get_diagnostics(self, tenant_id: Optional[str] = None,
                        period_minutes: int = 60) -> DiagnosticSummary:
        cutoff = datetime.now(timezone.utc).timestamp() - (period_minutes * 60)
        logs = [l for l in self._logs if l.timestamp.timestamp() > cutoff]
        if tenant_id:
            logs = [l for l in logs if l.tenant_id == tenant_id]

        total = len(logs)
        if total == 0:
            return DiagnosticSummary(period=f"last_{period_minutes}m")

        successful = sum(1 for l in logs if l.status == "success")
        failed = total - successful
        latencies = sorted([l.latency_ms for l in logs])
        total_tokens = sum(l.total_tokens for l in logs)
        total_cost = sum(l.cost_usd for l in logs)

        # Percentiles
        p50 = latencies[int(total * 0.5)] if total > 0 else 0
        p95 = latencies[int(total * 0.95)] if total > 0 else 0
        p99 = latencies[int(total * 0.99)] if total > 0 else 0

        # By model
        by_model = {}
        for l in logs:
            if l.model not in by_model:
                by_model[l.model] = {"count": 0, "tokens": 0, "cost": 0, "errors": 0, "avg_latency": 0}
            by_model[l.model]["count"] += 1
            by_model[l.model]["tokens"] += l.total_tokens
            by_model[l.model]["cost"] += l.cost_usd
            if l.status != "success":
                by_model[l.model]["errors"] += 1
        for m in by_model:
            by_model[m]["avg_latency"] = round(
                sum(l.latency_ms for l in logs if l.model == m) / by_model[m]["count"], 2
            )
            by_model[m]["cost"] = round(by_model[m]["cost"], 4)

        # By provider
        by_provider = {}
        for l in logs:
            if l.provider not in by_provider:
                by_provider[l.provider] = {"count": 0, "tokens": 0, "cost": 0}
            by_provider[l.provider]["count"] += 1
            by_provider[l.provider]["tokens"] += l.total_tokens
            by_provider[l.provider]["cost"] = round(by_provider[l.provider]["cost"] + l.cost_usd, 4)

        # By agent
        by_agent = {}
        for l in logs:
            if l.agent_id and l.agent_id not in by_agent:
                by_agent[l.agent_id] = {"count": 0, "tokens": 0, "cost": 0}
            if l.agent_id:
                by_agent[l.agent_id]["count"] += 1
                by_agent[l.agent_id]["tokens"] += l.total_tokens
                by_agent[l.agent_id]["cost"] = round(by_agent[l.agent_id]["cost"] + l.cost_usd, 4)

        # Top errors
        error_counts: Dict[str, int] = {}
        for l in logs:
            if l.error_message:
                error_counts[l.error_message] = error_counts.get(l.error_message, 0) + 1
        top_errors = [{"error": e, "count": c} for e, c in sorted(error_counts.items(), key=lambda x: -x[1])[:10]]

        return DiagnosticSummary(
            period=f"last_{period_minutes}m",
            total_requests=total, successful=successful, failed=failed,
            error_rate=round(failed / total * 100, 2) if total else 0,
            avg_latency_ms=round(sum(latencies) / total, 2),
            p50_latency_ms=round(p50, 2), p95_latency_ms=round(p95, 2), p99_latency_ms=round(p99, 2),
            total_tokens=total_tokens, total_cost_usd=round(total_cost, 4),
            avg_tokens_per_request=round(total_tokens / total, 1),
            requests_per_minute=round(total / max(period_minutes, 1), 2),
            by_model=by_model, by_provider=by_provider, by_agent=by_agent,
            by_status={"success": successful, "error": failed},
            top_errors=top_errors,
        )

    def get_stats(self) -> Dict:
        total = len(self._logs)
        return {
            "total_logs": total,
            "success": sum(1 for l in self._logs if l.status == "success"),
            "errors": sum(1 for l in self._logs if l.status != "success"),
            "models_seen": list(set(l.model for l in self._logs)),
            "providers_seen": list(set(l.provider for l in self._logs if l.provider)),
        }
