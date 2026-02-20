"""
JAI Agent OS — Langfuse Integration (HTTP-native)
Uses direct HTTP calls to Langfuse v2 REST API for maximum reliability.
Provides tracing, generation logging, scoring, and data fetching for the Monitoring UI.
"""

import uuid
import time
import httpx
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from collections import Counter

from backend.config.settings import settings


class LangfuseManager:
    """
    Langfuse integration using direct HTTP calls to the v2 REST API.
    Works reliably regardless of langfuse SDK version.
    """

    def __init__(self):
        self._host = settings.langfuse_host or ""
        self._public_key = settings.langfuse_public_key or ""
        self._secret_key = settings.langfuse_secret_key or ""
        # Persistent connection pool — reuses TCP connections across requests
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Lazy-init a persistent httpx.Client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self._host,
                auth=self._auth(),
                timeout=httpx.Timeout(10.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._client

    def _auth(self):
        return (self._public_key, self._secret_key)

    def is_configured(self) -> bool:
        return bool(self._public_key and self._secret_key)

    def is_ready(self) -> bool:
        return self.is_configured()

    def get_status(self) -> Dict[str, Any]:
        result = {"configured": self.is_configured(), "host": self._host, "initialized": self.is_configured()}
        if not self.is_configured():
            result["error"] = "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY not set"
            result["connected"] = False
            return result
        try:
            resp = self._get_client().get("/api/public/traces", params={"limit": 1}, timeout=5)
            result["connected"] = resp.status_code == 200
            if resp.status_code != 200:
                result["error"] = f"Langfuse API returned {resp.status_code}"
        except Exception as e:
            result["connected"] = False
            result["error"] = str(e)
        return result

    # ── Ingestion (batch API) ──────────────────────────────────────────

    def _ingest(self, events: List[Dict]) -> bool:
        """Send a batch of events to Langfuse ingestion API."""
        if not self.is_configured():
            return False
        try:
            resp = self._get_client().post(
                "/api/public/ingestion",
                json={"batch": events},
            )
            return resp.status_code == 200
        except Exception as e:
            print(f"[LANGFUSE] Ingestion error: {e}")
            return False

    def create_trace(
        self, name: str, user_id: Optional[str] = None,
        session_id: Optional[str] = None, metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None, input: Optional[Any] = None,
    ) -> Optional[str]:
        """Create a trace. Returns trace_id."""
        if not self.is_configured():
            return None
        trace_id = str(uuid.uuid4())
        event = {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "body": {
                "id": trace_id,
                "name": name,
                "userId": user_id,
                "sessionId": session_id,
                "metadata": metadata or {},
                "tags": tags or [],
                "input": input,
            },
        }
        self._ingest([event])
        return trace_id

    def update_trace(self, trace_id: str, output: Optional[Any] = None, metadata: Optional[Dict] = None):
        if not trace_id:
            return
        event = {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "body": {"id": trace_id},
        }
        if output is not None:
            event["body"]["output"] = output
        if metadata:
            event["body"]["metadata"] = metadata
        self._ingest([event])

    def log_generation(
        self, trace_id: Optional[str] = None, name: str = "llm-call",
        model: str = "", input: Optional[Any] = None, output: Optional[Any] = None,
        usage: Optional[Dict] = None, metadata: Optional[Dict] = None,
        level: str = "DEFAULT", start_time: Optional[str] = None, end_time: Optional[str] = None,
    ) -> Optional[str]:
        """Log an LLM generation to Langfuse. Returns observation_id."""
        if not self.is_configured():
            return None
        obs_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        if not trace_id:
            trace_id = self.create_trace(name=name)
        event = {
            "id": str(uuid.uuid4()),
            "type": "observation-create",
            "timestamp": now,
            "body": {
                "id": obs_id,
                "traceId": trace_id,
                "type": "GENERATION",
                "name": name,
                "model": model,
                "input": input,
                "output": output,
                "usage": usage,
                "metadata": metadata or {},
                "level": level,
                "startTime": start_time or now,
                "endTime": end_time or now,
            },
        }
        self._ingest([event])
        return obs_id

    def log_span(
        self, trace_id: Optional[str] = None, name: str = "operation",
        input: Optional[Any] = None, output: Optional[Any] = None,
        metadata: Optional[Dict] = None,
        start_time: Optional[str] = None, end_time: Optional[str] = None,
    ) -> Optional[str]:
        if not self.is_configured():
            return None
        obs_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        if not trace_id:
            trace_id = self.create_trace(name=name)
        event = {
            "id": str(uuid.uuid4()),
            "type": "observation-create",
            "timestamp": now,
            "body": {
                "id": obs_id,
                "traceId": trace_id,
                "type": "SPAN",
                "name": name,
                "input": input,
                "output": output,
                "metadata": metadata or {},
                "startTime": start_time or now,
                "endTime": end_time or now,
            },
        }
        self._ingest([event])
        return obs_id

    def score(self, trace_id: str, name: str, value: float,
              comment: Optional[str] = None, observation_id: Optional[str] = None) -> bool:
        if not self.is_configured():
            return False
        event = {
            "id": str(uuid.uuid4()),
            "type": "score-create",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "body": {
                "id": str(uuid.uuid4()),
                "traceId": trace_id,
                "name": name,
                "value": value,
                "comment": comment,
                "observationId": observation_id,
            },
        }
        return self._ingest([event])

    # ── LangChain Callback Handler ─────────────────────────────────────

    def get_langchain_handler(
        self, trace_name: Optional[str] = None, user_id: Optional[str] = None,
        session_id: Optional[str] = None, tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None, trace: Optional[Any] = None,
    ) -> Optional[Any]:
        # Tracing is handled via direct HTTP in the gateway; LangChain callback
        # disabled to avoid duplicate traces and SDK v3 incompatibilities.
        return None

    # ── Data Fetching (direct HTTP) ────────────────────────────────────

    def fetch_traces(self, limit: int = 50, name: Optional[str] = None,
                     user_id: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Dict]:
        if not self.is_configured():
            return []
        try:
            params = {"limit": limit}
            if name:
                params["name"] = name
            if user_id:
                params["userId"] = user_id
            resp = self._get_client().get("/api/public/traces", params=params)
            if resp.status_code != 200:
                return []
            results = []
            for t in resp.json().get("data", []):
                usage = t.get("usage") or {}
                inp_tok = usage.get("input") or 0
                out_tok = usage.get("output") or 0
                results.append({
                    "trace_id": t.get("id", ""),
                    "name": t.get("name", ""),
                    "timestamp": t.get("timestamp"),
                    "status": "error" if t.get("level") == "ERROR" else "success",
                    "latency_ms": t.get("latency"),
                    "input_tokens": inp_tok,
                    "output_tokens": out_tok,
                    "total_tokens": inp_tok + out_tok,
                    "total_cost": t.get("totalCost") or 0,
                    "user_id": t.get("userId"),
                    "session_id": t.get("sessionId"),
                    "tags": t.get("tags") or [],
                    "metadata": t.get("metadata") or {},
                    "input": str(t.get("input", ""))[:300] if t.get("input") else None,
                    "output": str(t.get("output", ""))[:300] if t.get("output") else None,
                })
            return results
        except Exception as e:
            print(f"[LANGFUSE] Error fetching traces: {e}")
            return []

    def fetch_generations(self, limit: int = 50, name: Optional[str] = None,
                          model: Optional[str] = None) -> List[Dict]:
        if not self.is_configured():
            return []
        try:
            params = {"limit": limit, "type": "GENERATION"}
            if name:
                params["name"] = name
            resp = self._get_client().get("/api/public/observations", params=params)
            if resp.status_code != 200:
                return []
            results = []
            for g in resp.json().get("data", []):
                if model and g.get("model") != model:
                    continue
                usage = g.get("usage") or {}
                inp_tok = usage.get("input") or usage.get("promptTokens") or 0
                out_tok = usage.get("output") or usage.get("completionTokens") or 0
                total_tok = usage.get("total") or usage.get("totalTokens") or (inp_tok + out_tok)
                latency = None
                st, et = g.get("startTime"), g.get("endTime")
                if st and et:
                    try:
                        s = datetime.fromisoformat(st.replace("Z", "+00:00"))
                        e = datetime.fromisoformat(et.replace("Z", "+00:00"))
                        latency = (e - s).total_seconds() * 1000
                    except Exception:
                        pass
                results.append({
                    "generation_id": g.get("id", ""),
                    "trace_id": g.get("traceId", ""),
                    "name": g.get("name", ""),
                    "model": g.get("model", ""),
                    "timestamp": st,
                    "status": "error" if g.get("level") == "ERROR" else "success",
                    "latency_ms": round(latency, 1) if latency else None,
                    "input_tokens": inp_tok,
                    "output_tokens": out_tok,
                    "total_tokens": total_tok,
                    "total_cost": g.get("calculatedTotalCost") or 0,
                    "input": str(g.get("input", ""))[:300] if g.get("input") else None,
                    "output": str(g.get("output", ""))[:300] if g.get("output") else None,
                    "metadata": g.get("metadata") or {},
                })
            return results
        except Exception as e:
            print(f"[LANGFUSE] Error fetching generations: {e}")
            return []

    def fetch_scores(self, limit: int = 50) -> List[Dict]:
        if not self.is_configured():
            return []
        try:
            resp = self._get_client().get("/api/public/scores", params={"limit": limit})
            if resp.status_code != 200:
                return []
            results = []
            for s in resp.json().get("data", []):
                results.append({
                    "score_id": s.get("id", ""),
                    "trace_id": s.get("traceId", ""),
                    "observation_id": s.get("observationId", ""),
                    "name": s.get("name", ""),
                    "value": s.get("value"),
                    "comment": s.get("comment"),
                    "timestamp": s.get("timestamp"),
                })
            return results
        except Exception as e:
            print(f"[LANGFUSE] Error fetching scores: {e}")
            return []

    def fetch_sessions(self, limit: int = 50) -> List[Dict]:
        if not self.is_configured():
            return []
        try:
            resp = self._get_client().get("/api/public/sessions", params={"limit": limit})
            if resp.status_code != 200:
                return []
            results = []
            for s in resp.json().get("data", []):
                results.append({
                    "session_id": s.get("id", ""),
                    "created_at": s.get("createdAt"),
                    "trace_count": s.get("countTraces") or 0,
                })
            return results
        except Exception as e:
            print(f"[LANGFUSE] Error fetching sessions: {e}")
            return []

    def fetch_trace_detail(self, trace_id: str) -> Optional[Dict]:
        if not self.is_configured():
            return None
        try:
            client = self._get_client()
            resp = client.get(f"/api/public/traces/{trace_id}")
            if resp.status_code != 200:
                return None
            t = resp.json()
            obs_resp = client.get("/api/public/observations",
                                 params={"traceId": trace_id, "limit": 100})
            observations = []
            if obs_resp.status_code == 200:
                for o in obs_resp.json().get("data", []):
                    start, end = o.get("startTime"), o.get("endTime") or o.get("completionStartTime")
                    latency = None
                    if start and end:
                        try:
                            s = datetime.fromisoformat(start.replace("Z", "+00:00"))
                            e = datetime.fromisoformat(end.replace("Z", "+00:00"))
                            latency = (e - s).total_seconds() * 1000
                        except Exception:
                            pass
                    usage = o.get("usage") or {}
                    observations.append({
                        "id": o.get("id", ""), "type": o.get("type", "SPAN"),
                        "name": o.get("name", ""), "model": o.get("model"),
                        "start_time": start, "end_time": end,
                        "latency_ms": round(latency, 1) if latency else None,
                        "level": o.get("level", "DEFAULT"),
                        "status": "error" if o.get("level") == "ERROR" else "success",
                        "input": str(o.get("input", ""))[:500] if o.get("input") else None,
                        "output": str(o.get("output", ""))[:500] if o.get("output") else None,
                        "input_tokens": usage.get("input") or usage.get("promptTokens") or 0,
                        "output_tokens": usage.get("output") or usage.get("completionTokens") or 0,
                        "total_tokens": usage.get("total") or usage.get("totalTokens") or 0,
                        "total_cost": o.get("calculatedTotalCost") or 0,
                        "metadata": o.get("metadata") or {},
                        "parent_observation_id": o.get("parentObservationId"),
                    })
            observations.sort(key=lambda x: x.get("start_time") or "")
            usage = t.get("usage") or {}
            return {
                "trace_id": t.get("id", ""), "name": t.get("name", ""),
                "timestamp": t.get("timestamp"),
                "status": "error" if t.get("level") == "ERROR" else "success",
                "input": str(t.get("input", ""))[:500] if t.get("input") else None,
                "output": str(t.get("output", ""))[:500] if t.get("output") else None,
                "user_id": t.get("userId"), "session_id": t.get("sessionId"),
                "tags": t.get("tags") or [], "metadata": t.get("metadata") or {},
                "latency_ms": t.get("latency"),
                "input_tokens": usage.get("input") or 0,
                "output_tokens": usage.get("output") or 0,
                "total_tokens": usage.get("total") or 0,
                "total_cost": t.get("totalCost") or 0,
                "observations": observations,
            }
        except Exception as e:
            print(f"[LANGFUSE] Error fetching trace detail: {e}")
            return None

    def fetch_metrics(self) -> Dict:
        if not self.is_configured():
            return {}
        try:
            client = self._get_client()
            resp = client.get("/api/public/traces", params={"limit": 100})
            traces = resp.json().get("data", []) if resp.status_code == 200 else []
            obs_resp = client.get("/api/public/observations",
                                  params={"limit": 100, "type": "GENERATION"})
            generations = obs_resp.json().get("data", []) if obs_resp.status_code == 200 else []

            total_traces = len(traces)
            total_cost = sum(t.get("totalCost") or 0 for t in traces)
            total_tokens = sum((t.get("usage") or {}).get("total") or 0 for t in traces)
            latencies = [t.get("latency") for t in traces if t.get("latency")]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else (latencies[0] if latencies else 0)
            error_count = sum(1 for t in traces if t.get("level") == "ERROR")

            model_stats = {}
            for g in generations:
                m = g.get("model") or "unknown"
                if m not in model_stats:
                    model_stats[m] = {"count": 0, "tokens": 0, "cost": 0, "latencies": []}
                model_stats[m]["count"] += 1
                usage = g.get("usage") or {}
                model_stats[m]["tokens"] += usage.get("total") or usage.get("totalTokens") or 0
                model_stats[m]["cost"] += g.get("calculatedTotalCost") or 0
                lat = g.get("latency")
                if lat:
                    model_stats[m]["latencies"].append(lat)

            model_breakdown = []
            for m, s in sorted(model_stats.items(), key=lambda x: -x[1]["count"]):
                avg_lat = sum(s["latencies"]) / len(s["latencies"]) if s["latencies"] else 0
                model_breakdown.append({"model": m, "count": s["count"], "tokens": s["tokens"],
                                         "cost": round(s["cost"], 6), "avg_latency_ms": round(avg_lat, 1)})

            daily = Counter()
            for t in traces:
                ts = t.get("timestamp", "")
                if ts:
                    daily[ts[:10]] += 1

            return {
                "total_traces": total_traces, "total_cost": round(total_cost, 6),
                "total_tokens": total_tokens, "avg_latency_ms": round(avg_latency, 1),
                "p95_latency_ms": round(p95_latency, 1), "error_count": error_count,
                "error_rate": round(error_count / total_traces * 100, 1) if total_traces else 0,
                "model_breakdown": model_breakdown,
                "daily_counts": [{"date": d, "count": c} for d, c in sorted(daily.items())],
            }
        except Exception as e:
            print(f"[LANGFUSE] Error fetching metrics: {e}")
            return {}

    # ── Flush & Shutdown ───────────────────────────────────────────────

    def flush(self):
        pass  # HTTP calls are synchronous, no buffering

    def shutdown(self):
        if self._client and not self._client.is_closed:
            self._client.close()
            self._client = None
