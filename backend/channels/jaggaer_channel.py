"""
Jaggaer SaaS Channel - REST API connector for making LLM calls from Jaggaer platform.
Provides a standardized interface for Jaggaer SaaS to invoke Agent Studio LLM capabilities
with multi-tenancy, rate limiting, and usage tracking.
"""

import uuid
import time
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from backend.config.settings import settings
from backend.llm_registry.provider_factory import ProviderFactory
from backend.llm_registry.model_library import ModelLibrary


class LLMCallType(str, Enum):
    COMPLETION = "completion"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    AGENT_STEP = "agent_step"


class LLMCallRequest(BaseModel):
    """Inbound LLM call request from Jaggaer SaaS."""
    request_id: str = Field(default_factory=lambda: f"REQ-{uuid.uuid4().hex[:8].upper()}")
    tenant_id: str
    user_id: str = ""
    call_type: LLMCallType = LLMCallType.COMPLETION
    model_id: Optional[str] = None  # if None, auto-select based on call_type
    prompt: str
    system_prompt: Optional[str] = None
    variables: Dict[str, str] = Field(default_factory=dict)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    structured_output_schema: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMCallResponse(BaseModel):
    """Response from an LLM call."""
    request_id: str
    model_id: str
    model_name: str
    provider: str
    response: str = ""
    structured_output: Optional[Dict[str, Any]] = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UsageRecord(BaseModel):
    """Usage tracking record for billing and metering."""
    record_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    tenant_id: str
    user_id: str
    model_id: str
    call_type: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Default model routing by call type ────────────────────────────────────────

DEFAULT_MODEL_ROUTING: Dict[LLMCallType, str] = {
    LLMCallType.COMPLETION: "gemini-2.5-flash",
    LLMCallType.CLASSIFICATION: "gemini-2.0-flash",
    LLMCallType.EXTRACTION: "gemini-2.5-flash",
    LLMCallType.SUMMARIZATION: "gemini-2.5-flash",
    LLMCallType.AGENT_STEP: "gemini-2.5-pro",
}


class JaggaerChannel:
    """
    REST API channel for Jaggaer SaaS to make LLM calls through Agent Studio.
    Handles model routing, rate limiting, usage tracking, and multi-tenancy.
    """

    def __init__(
        self,
        library: Optional[ModelLibrary] = None,
        factory: Optional[ProviderFactory] = None,
    ):
        self._library = library or ModelLibrary()
        self._factory = factory or ProviderFactory(self._library)
        self._usage: List[UsageRecord] = []
        self._rate_limits: Dict[str, List[float]] = {}  # tenant_id -> list of timestamps

    def _check_rate_limit(self, tenant_id: str) -> bool:
        """Check if tenant is within rate limit."""
        now = time.time()
        window = 60.0  # 1 minute window
        limit = settings.api_rate_limit_per_minute

        if tenant_id not in self._rate_limits:
            self._rate_limits[tenant_id] = []

        # Prune old entries
        self._rate_limits[tenant_id] = [
            ts for ts in self._rate_limits[tenant_id] if now - ts < window
        ]

        if len(self._rate_limits[tenant_id]) >= limit:
            return False

        self._rate_limits[tenant_id].append(now)
        return True

    def _resolve_model(self, request: LLMCallRequest) -> str:
        """Resolve model_id from request or default routing."""
        if request.model_id:
            model = self._library.get(request.model_id)
            if model:
                return request.model_id
        return DEFAULT_MODEL_ROUTING.get(request.call_type, "gemini-2.5-flash")

    async def invoke(self, request: LLMCallRequest) -> LLMCallResponse:
        """
        Process an LLM call request from Jaggaer SaaS.
        Handles model resolution, invocation, usage tracking, and rate limiting.
        """
        # Rate limit check
        if not self._check_rate_limit(request.tenant_id):
            return LLMCallResponse(
                request_id=request.request_id,
                model_id="",
                model_name="",
                provider="",
                success=False,
                error=f"Rate limit exceeded ({settings.api_rate_limit_per_minute}/min)",
            )

        model_id = self._resolve_model(request)
        model = self._library.get(model_id)
        if not model:
            return LLMCallResponse(
                request_id=request.request_id,
                model_id=model_id,
                model_name="unknown",
                provider="unknown",
                success=False,
                error=f"Model '{model_id}' not available",
            )

        # Build prompt
        prompt = request.prompt
        for key, value in request.variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

        messages = []
        if request.system_prompt:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=request.system_prompt), HumanMessage(content=prompt)]
        else:
            from langchain_core.messages import HumanMessage
            messages = [HumanMessage(content=prompt)]

        try:
            llm = self._factory.create(
                model_id,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            start = time.time()
            response = llm.invoke(messages)
            latency_ms = (time.time() - start) * 1000

            content = response.content if hasattr(response, "content") else str(response)
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "input_tokens", 0) if usage else len(prompt) // 4
            output_tokens = getattr(usage, "output_tokens", 0) if usage else len(content) // 4
            cost = model.pricing.estimate_cost(input_tokens, output_tokens)

            # Track usage
            self._usage.append(UsageRecord(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                model_id=model_id,
                call_type=request.call_type.value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
            ))

            return LLMCallResponse(
                request_id=request.request_id,
                model_id=model_id,
                model_name=model.display_name,
                provider=model.provider.value,
                response=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=round(latency_ms, 1),
                cost_usd=round(cost, 6),
            )

        except Exception as e:
            return LLMCallResponse(
                request_id=request.request_id,
                model_id=model_id,
                model_name=model.display_name,
                provider=model.provider.value,
                success=False,
                error=str(e),
            )

    def get_usage(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[UsageRecord]:
        records = self._usage
        if tenant_id:
            records = [r for r in records if r.tenant_id == tenant_id]
        return sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]

    def get_usage_summary(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get aggregated usage summary."""
        records = self.get_usage(tenant_id, limit=10000)
        if not records:
            return {"total_calls": 0, "total_tokens": 0, "total_cost": 0.0}

        by_model: Dict[str, Dict[str, Any]] = {}
        for r in records:
            if r.model_id not in by_model:
                by_model[r.model_id] = {"calls": 0, "tokens": 0, "cost": 0.0}
            by_model[r.model_id]["calls"] += 1
            by_model[r.model_id]["tokens"] += r.input_tokens + r.output_tokens
            by_model[r.model_id]["cost"] += r.cost_usd

        return {
            "total_calls": len(records),
            "total_tokens": sum(r.input_tokens + r.output_tokens for r in records),
            "total_cost": round(sum(r.cost_usd for r in records), 4),
            "avg_latency_ms": round(sum(r.latency_ms for r in records) / len(records), 1),
            "by_model": by_model,
        }
