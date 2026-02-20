"""
JAI Agent OS — Agent-as-a-Service (AaaS) Gateway
OpenAI-compatible REST API that abstracts LLM calls from SaaS applications.
Supports /v1/chat/completions, API key auth, rate limiting, tenant isolation.
Designed for GKE horizontal scaling to 1000+ LLM req/sec.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import hashlib
import time
import asyncio


class GatewayRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    model: str = "gemini-2.5-flash"
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    stream: bool = False
    # JAI extensions
    agent_id: Optional[str] = None
    tenant_id: Optional[str] = None
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GatewayChoice(BaseModel):
    index: int = 0
    message: Dict[str, Any] = Field(default_factory=dict)
    finish_reason: str = "stop"


class GatewayUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GatewayResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    id: str = ""
    object: str = "chat.completion"
    created: int = 0
    model: str = ""
    choices: List[GatewayChoice] = Field(default_factory=list)
    usage: GatewayUsage = Field(default_factory=GatewayUsage)
    # JAI extensions
    agent_id: Optional[str] = None
    tenant_id: Optional[str] = None
    latency_ms: float = 0
    cost_usd: float = 0


class RateLimiter:
    """Token-bucket rate limiter per tenant."""

    def __init__(self):
        self._buckets: Dict[str, Dict] = {}

    def check(self, tenant_id: str, rpm_limit: int) -> bool:
        now = time.time()
        bucket = self._buckets.get(tenant_id)
        if not bucket or now - bucket["window_start"] > 60:
            self._buckets[tenant_id] = {"window_start": now, "count": 0}
            bucket = self._buckets[tenant_id]
        return bucket["count"] < rpm_limit

    def record(self, tenant_id: str):
        bucket = self._buckets.get(tenant_id)
        if bucket:
            bucket["count"] += 1


class RequestLog(BaseModel):
    request_id: str = ""
    tenant_id: str = ""
    agent_id: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0
    cost_usd: float = 0
    status: str = "success"
    error: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict = Field(default_factory=dict)


class AgentGateway:
    """
    Agent-as-a-Service gateway providing OpenAI-compatible API.
    Acts as an LLM-lite abstraction layer for SaaS applications.
    """

    def __init__(self):
        self._rate_limiter = RateLimiter()
        self._request_logs: List[RequestLog] = []
        self._model_routing: Dict[str, str] = {}
        self._request_count = 0

    async def process_completion(self, request: GatewayRequest,
                                  tenant_id: str = "tenant-default",
                                  llm_registry=None,
                                  langfuse_manager=None,
                                  provider_factory=None,
                                  integration_manager=None,
                                  model_library=None) -> GatewayResponse:
        """Process an OpenAI-compatible chat completion request."""
        start = time.time()
        self._request_count += 1
        req_id = f"chatcmpl-{hashlib.md5(f'{self._request_count}-{start}'.encode()).hexdigest()[:12]}"

        # Create Langfuse trace for this request
        lf_trace_id = None
        if langfuse_manager and langfuse_manager.is_ready():
            lf_trace_id = langfuse_manager.create_trace(
                name="gateway-completion",
                user_id=request.metadata.get("user_id"),
                session_id=request.metadata.get("session_id"),
                metadata={"tenant_id": tenant_id, "agent_id": request.agent_id or "", "request_id": req_id},
                tags=["gateway", request.model],
                input={"model": request.model, "messages": request.messages, "temperature": request.temperature},
            )

        try:
            # Route to appropriate model
            model_id = self._resolve_model(request.model, tenant_id)

            # Call LLM via provider_factory (real call) or fallback to simulated
            response_text = ""
            prompt_tokens = 0
            completion_tokens = 0

            if provider_factory and model_library:
                # Real LLM call via LangChain + provider_factory
                model_entry = model_library.get(model_id)
                if model_entry:
                    # Look up integration credentials (API key or service account)
                    extra_kwargs = {}
                    credential_data = None
                    intg_id = (model_entry.metadata or {}).get("integration_id")
                    if intg_id and integration_manager:
                        intg = integration_manager.get(intg_id)
                        if intg:
                            if intg.auth_type == "api_key" and intg.api_key:
                                extra_kwargs["google_api_key"] = intg.api_key
                            elif intg.auth_type == "service_account" and intg.service_account_json:
                                credential_data = intg.service_account_json

                    llm = provider_factory.create(
                        model_id,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        credential_data=credential_data,
                        langfuse_trace_name="gateway-completion",
                        langfuse_user_id=request.metadata.get("user_id"),
                        langfuse_tags=["gateway", model_id],
                        **extra_kwargs,
                    )
                    response = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: llm.invoke(request.messages)
                    )
                    response_text = response.content if hasattr(response, "content") else str(response)
                    usage = getattr(response, "usage_metadata", None)
                    if usage and isinstance(usage, dict):
                        prompt_tokens = usage.get("input_tokens", 0) or 0
                        completion_tokens = usage.get("output_tokens", 0) or 0
                    elif usage:
                        prompt_tokens = getattr(usage, "input_tokens", 0) or 0
                        completion_tokens = getattr(usage, "output_tokens", 0) or 0
                    else:
                        prompt_tokens = sum(len(m.get("content", "").split()) * 2 for m in request.messages)
                        completion_tokens = len(response_text.split()) * 2
                else:
                    # Model not in library — simulated response
                    prompt_tokens = sum(len(m.get("content", "").split()) * 2 for m in request.messages)
                    response_text = f"[JAI Agent OS] Model '{model_id}' not registered. Add it via Model Library."
                    completion_tokens = len(response_text.split()) * 2
            elif llm_registry:
                prompt = self._messages_to_prompt(request.messages)
                result = await llm_registry.call_model(
                    model_id=model_id, prompt=prompt,
                    temperature=request.temperature, max_tokens=request.max_tokens,
                )
                response_text = result.get("response", "")
                prompt_tokens = result.get("input_tokens", 0)
                completion_tokens = result.get("output_tokens", 0)
            else:
                # Simulated response for testing
                prompt_tokens = sum(len(m.get("content", "").split()) * 2 for m in request.messages)
                response_text = f"[JAI Agent OS] Processed by {model_id}. This is a gateway response."
                completion_tokens = len(response_text.split()) * 2

            latency_ms = (time.time() - start) * 1000
            total_tokens = prompt_tokens + completion_tokens
            cost = self._estimate_cost(model_id, prompt_tokens, completion_tokens)

            response = GatewayResponse(
                id=req_id,
                created=int(time.time()),
                model=model_id,
                choices=[GatewayChoice(
                    index=0,
                    message={"role": "assistant", "content": response_text},
                    finish_reason="stop",
                )],
                usage=GatewayUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                ),
                agent_id=request.agent_id,
                tenant_id=tenant_id,
                latency_ms=round(latency_ms, 2),
                cost_usd=round(cost, 6),
            )

            # Log request
            self._log_request(RequestLog(
                request_id=req_id, tenant_id=tenant_id,
                agent_id=request.agent_id or "", model=model_id,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                total_tokens=total_tokens, latency_ms=round(latency_ms, 2),
                cost_usd=round(cost, 6), status="success",
                metadata=request.metadata,
            ))

            # Log generation to Langfuse
            if lf_trace_id and langfuse_manager:
                from datetime import datetime as _dt, timezone as _tz
                end_ts = _dt.now(_tz.utc).isoformat()
                langfuse_manager.log_generation(
                    trace_id=lf_trace_id,
                    name="chat-completion",
                    model=model_id,
                    input={"messages": request.messages},
                    output={"content": response_text},
                    usage={"input": prompt_tokens, "output": completion_tokens, "total": total_tokens, "unit": "TOKENS"},
                    metadata={"cost_usd": round(cost, 6), "latency_ms": round(latency_ms, 2)},
                    end_time=end_ts,
                )
                langfuse_manager.update_trace(lf_trace_id, output={"content": response_text[:200], "model": model_id, "tokens": total_tokens})

            return response

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            self._log_request(RequestLog(
                request_id=req_id, tenant_id=tenant_id,
                agent_id=request.agent_id or "", model=request.model,
                latency_ms=round(latency_ms, 2), status="error",
                error=str(e),
            ))

            # Log error to Langfuse
            if lf_trace_id and langfuse_manager:
                langfuse_manager.log_generation(
                    trace_id=lf_trace_id,
                    name="chat-completion",
                    model=request.model,
                    input={"messages": request.messages},
                    output={"error": str(e)},
                    level="ERROR",
                    metadata={"latency_ms": round(latency_ms, 2)},
                )
                langfuse_manager.update_trace(lf_trace_id, output={"error": str(e)})

            raise

    def check_rate_limit(self, tenant_id: str, rpm_limit: int) -> bool:
        return self._rate_limiter.check(tenant_id, rpm_limit)

    def record_rate_limit(self, tenant_id: str):
        self._rate_limiter.record(tenant_id)

    def _resolve_model(self, model: str, tenant_id: str) -> str:
        key = f"{tenant_id}:{model}"
        return self._model_routing.get(key, model)

    def set_model_routing(self, tenant_id: str, alias: str, target: str):
        self._model_routing[f"{tenant_id}:{alias}"] = target

    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                content = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
            parts.append(f"{role}: {content}")
        return "\n".join(parts)

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        costs = {
            "gemini-2.0-flash": (0.0001, 0.0004),
            "gemini-2.5-flash": (0.00015, 0.0006),
            "gemini-2.5-pro": (0.00125, 0.005),
            "claude-sonnet-4-20250514": (0.003, 0.015),
            "claude-3-5-haiku-20241022": (0.0008, 0.004),
            "gpt-4o": (0.0025, 0.01),
            "gpt-4o-mini": (0.00015, 0.0006),
        }
        rate = costs.get(model, (0.001, 0.002))
        return (input_tokens / 1000 * rate[0]) + (output_tokens / 1000 * rate[1])

    def _log_request(self, log: RequestLog):
        self._request_logs.append(log)
        if len(self._request_logs) > 10000:
            self._request_logs = self._request_logs[-5000:]

    def get_logs(self, tenant_id: Optional[str] = None, limit: int = 100,
                 status: Optional[str] = None) -> List[RequestLog]:
        logs = self._request_logs
        if tenant_id:
            logs = [l for l in logs if l.tenant_id == tenant_id]
        if status:
            logs = [l for l in logs if l.status == status]
        return sorted(logs, key=lambda l: l.timestamp, reverse=True)[:limit]

    def get_stats(self, tenant_id: Optional[str] = None) -> Dict:
        logs = self._request_logs
        if tenant_id:
            logs = [l for l in logs if l.tenant_id == tenant_id]
        total = len(logs)
        success = sum(1 for l in logs if l.status == "success")
        errors = total - success
        total_tokens = sum(l.total_tokens for l in logs)
        total_cost = sum(l.cost_usd for l in logs)
        avg_latency = sum(l.latency_ms for l in logs) / total if total else 0
        return {
            "total_requests": total, "successful": success, "errors": errors,
            "total_tokens": total_tokens, "total_cost_usd": round(total_cost, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "models_used": list(set(l.model for l in logs)),
        }
