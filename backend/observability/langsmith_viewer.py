"""
LangSmith Viewer - Access traces, runs, feedback, and cost analytics from LangSmith API.
Provides a unified interface for the Agent Studio UI to browse observability data.
"""

import os
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from backend.config.settings import settings


class TraceInfo(BaseModel):
    """Summary of a LangSmith trace."""
    run_id: str
    name: str
    run_type: str = ""
    status: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    latency_ms: Optional[float] = None
    total_tokens: int = 0
    total_cost: float = 0.0
    error: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeedbackInfo(BaseModel):
    """Summary of LangSmith feedback on a run."""
    feedback_id: str
    run_id: str
    key: str
    score: Optional[float] = None
    value: Optional[str] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


class LangSmithViewer:
    """
    Read-only viewer for LangSmith traces, runs, and feedback.
    Uses the LangSmith Python SDK to query the API.
    """

    def __init__(self):
        self._client = None
        self._project_name = settings.langchain_project

    def _ensure_client(self):
        """Lazy-initialize the LangSmith client."""
        if self._client is None:
            try:
                from langsmith import Client
                os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key or ""
                os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
                self._client = Client()
            except ImportError:
                raise RuntimeError("langsmith package not installed. Run: pip install langsmith")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize LangSmith client: {e}")

    def is_configured(self) -> bool:
        """Check if LangSmith API key is configured."""
        return bool(settings.langchain_api_key)

    def get_project_info(self) -> Dict[str, Any]:
        """Get info about the configured LangSmith project."""
        if not self.is_configured():
            return {"configured": False, "error": "LANGCHAIN_API_KEY not set"}

        try:
            self._ensure_client()
            project = self._client.read_project(project_name=self._project_name)
            return {
                "configured": True,
                "project_name": self._project_name,
                "project_id": str(project.id),
                "created_at": str(project.created_at) if project.created_at else None,
                "run_count": getattr(project, "run_count", None),
                "endpoint": settings.langchain_endpoint,
            }
        except Exception as e:
            return {"configured": True, "error": str(e)}

    def list_runs(
        self,
        limit: int = 20,
        run_type: Optional[str] = None,
        error_only: bool = False,
        start_time: Optional[datetime] = None,
    ) -> List[TraceInfo]:
        """
        List recent runs from LangSmith.

        Args:
            limit: Max runs to return
            run_type: Filter by type ('chain', 'llm', 'tool', 'retriever')
            error_only: Only return failed runs
            start_time: Only return runs after this time
        """
        self._ensure_client()

        kwargs: Dict[str, Any] = {
            "project_name": self._project_name,
            "limit": limit,
        }
        if run_type:
            kwargs["run_type"] = run_type
        if error_only:
            kwargs["error"] = True
        if start_time:
            kwargs["start_time"] = start_time

        traces = []
        try:
            for run in self._client.list_runs(**kwargs):
                latency = None
                if run.start_time and run.end_time:
                    latency = (run.end_time - run.start_time).total_seconds() * 1000

                tokens = 0
                cost = 0.0
                if hasattr(run, "total_tokens"):
                    tokens = run.total_tokens or 0
                if hasattr(run, "total_cost"):
                    cost = run.total_cost or 0.0

                traces.append(TraceInfo(
                    run_id=str(run.id),
                    name=run.name or "",
                    run_type=run.run_type or "",
                    status="error" if run.error else "success",
                    start_time=run.start_time,
                    end_time=run.end_time,
                    latency_ms=round(latency, 1) if latency else None,
                    total_tokens=tokens,
                    total_cost=round(cost, 6),
                    error=run.error,
                    tags=run.tags or [],
                    metadata=run.extra or {},
                ))
        except Exception as e:
            print(f"[LANGSMITH] Error listing runs: {e}")

        return traces

    def get_run_detail(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific run."""
        self._ensure_client()

        try:
            run = self._client.read_run(run_id)
            child_runs = []
            try:
                for child in self._client.list_runs(
                    parent_run_id=run_id,
                    project_name=self._project_name,
                    limit=50,
                ):
                    child_runs.append({
                        "run_id": str(child.id),
                        "name": child.name,
                        "run_type": child.run_type,
                        "status": "error" if child.error else "success",
                        "latency_ms": round(
                            (child.end_time - child.start_time).total_seconds() * 1000, 1
                        ) if child.start_time and child.end_time else None,
                    })
            except Exception:
                pass

            return {
                "run_id": str(run.id),
                "name": run.name,
                "run_type": run.run_type,
                "status": "error" if run.error else "success",
                "start_time": str(run.start_time) if run.start_time else None,
                "end_time": str(run.end_time) if run.end_time else None,
                "inputs": run.inputs,
                "outputs": run.outputs,
                "error": run.error,
                "tags": run.tags or [],
                "total_tokens": getattr(run, "total_tokens", 0),
                "total_cost": getattr(run, "total_cost", 0.0),
                "child_runs": child_runs,
                "feedback": self._get_run_feedback(run_id),
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_run_feedback(self, run_id: str) -> List[Dict[str, Any]]:
        """Get feedback for a specific run."""
        try:
            feedbacks = []
            for fb in self._client.list_feedback(run_ids=[run_id]):
                feedbacks.append({
                    "feedback_id": str(fb.id),
                    "key": fb.key,
                    "score": fb.score,
                    "value": fb.value,
                    "comment": fb.comment,
                    "created_at": str(fb.created_at) if fb.created_at else None,
                })
            return feedbacks
        except Exception:
            return []

    def get_run_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get aggregated run statistics for the last N hours."""
        self._ensure_client()
        start = datetime.utcnow() - timedelta(hours=hours)

        runs = self.list_runs(limit=1000, start_time=start)

        if not runs:
            return {"period_hours": hours, "total_runs": 0}

        success = [r for r in runs if r.status == "success"]
        errors = [r for r in runs if r.status == "error"]
        latencies = [r.latency_ms for r in runs if r.latency_ms is not None]

        by_type: Dict[str, int] = {}
        for r in runs:
            by_type[r.run_type] = by_type.get(r.run_type, 0) + 1

        return {
            "period_hours": hours,
            "total_runs": len(runs),
            "success_count": len(success),
            "error_count": len(errors),
            "success_rate": round(len(success) / len(runs) * 100, 1) if runs else 0,
            "total_tokens": sum(r.total_tokens for r in runs),
            "total_cost": round(sum(r.total_cost for r in runs), 4),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 1),
            "by_run_type": by_type,
        }

    def create_feedback(
        self,
        run_id: str,
        key: str,
        score: Optional[float] = None,
        value: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create feedback on a LangSmith run."""
        self._ensure_client()
        try:
            fb = self._client.create_feedback(
                run_id=run_id,
                key=key,
                score=score,
                value=value,
                comment=comment,
            )
            return {"feedback_id": str(fb.id), "success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
