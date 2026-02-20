"""
Agent Orchestrator — Connect multiple agents into coordinated workflows.
Supports sequential pipelines, parallel fan-out, hub-and-spoke supervisor,
and conditional routing patterns. Follows OAP supervisor agent pattern.
"""

import uuid
import copy
import time
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

# Bounded concurrency for parallel execution patterns
_PARALLEL_SEMAPHORE = asyncio.Semaphore(10)


class OrchestrationPattern(str, Enum):
    SEQUENTIAL = "sequential"      # A → B → C
    PARALLEL = "parallel"          # A + B + C (fan-out, merge)
    SUPERVISOR = "supervisor"      # Hub routes to spoke agents
    CONDITIONAL = "conditional"    # Route based on conditions
    MAP_REDUCE = "map_reduce"      # Split input, process in parallel, merge


class PipelineStep(BaseModel):
    """A single step in an orchestration pipeline."""
    step_id: str = Field(default_factory=lambda: f"step-{uuid.uuid4().hex[:6]}")
    agent_id: str
    agent_name: str = ""
    order: int = 0
    input_mapping: Dict[str, str] = Field(default_factory=dict)  # step output key -> agent input key
    output_key: str = ""  # key to store this step's output
    condition: Optional[str] = None  # for conditional routing
    timeout_seconds: int = 120
    retry_count: int = 2
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Pipeline(BaseModel):
    """An orchestration pipeline connecting multiple agents."""
    pipeline_id: str = Field(default_factory=lambda: f"pipe-{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    pattern: OrchestrationPattern = OrchestrationPattern.SEQUENTIAL
    steps: List[PipelineStep] = Field(default_factory=list)
    supervisor_agent_id: Optional[str] = None  # for supervisor pattern
    tags: List[str] = Field(default_factory=list)
    version: int = 1
    status: str = "draft"  # draft, active, paused, archived
    owner_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PipelineRun(BaseModel):
    """Record of a pipeline execution."""
    run_id: str = Field(default_factory=lambda: f"prun-{uuid.uuid4().hex[:8]}")
    pipeline_id: str
    pipeline_name: str = ""
    status: str = "running"  # running, completed, failed, cancelled
    pattern: str = ""
    steps_completed: int = 0
    steps_total: int = 0
    step_results: List[Dict[str, Any]] = Field(default_factory=list)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    error: Optional[str] = None


class AgentOrchestrator:
    """
    Manages orchestration pipelines and executes multi-agent workflows.
    PostgreSQL-backed with in-memory fallback.
    """

    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._versions: Dict[str, List[Pipeline]] = {}
        self._runs: List[PipelineRun] = []
        self._db_available = False

    def _sf(self):
        from backend.db.sync_bridge import get_session_factory
        return get_session_factory()

    # ── Async DB helpers ──────────────────────────────────────────

    async def _db_create_pipeline(self, pipe: Pipeline) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from backend.db.models import PipelineModel
        async with factory() as session:
            row = PipelineModel(
                id=pipe.pipeline_id, name=pipe.name, description=pipe.description,
                pattern=pipe.pattern.value,
                steps_json=[s.model_dump() for s in pipe.steps],
                supervisor_agent_id=pipe.supervisor_agent_id,
                tags=pipe.tags, version=pipe.version, status=pipe.status,
                owner_id=pipe.owner_id, metadata_json=pipe.metadata,
            )
            session.add(row)
            await session.commit()
            return True

    async def _db_update_pipeline(self, pipeline_id, updates) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import PipelineModel
        async with factory() as session:
            row = (await session.execute(
                select(PipelineModel).where(PipelineModel.id == pipeline_id)
            )).scalar_one_or_none()
            if not row:
                return False
            for k, v in updates.items():
                if k == "steps" and hasattr(row, "steps_json"):
                    row.steps_json = [s.model_dump() if hasattr(s, 'model_dump') else s for s in v]
                elif k == "pattern" and hasattr(row, "pattern"):
                    row.pattern = v.value if hasattr(v, 'value') else v
                elif k == "metadata" and hasattr(row, "metadata_json"):
                    row.metadata_json = v
                elif hasattr(row, k) and k not in ("id", "created_at"):
                    setattr(row, k, v)
            row.version = (row.version or 1) + 1
            row.updated_at = datetime.utcnow()
            await session.commit()
            return True

    async def _db_delete_pipeline(self, pipeline_id) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import PipelineModel
        async with factory() as session:
            row = (await session.execute(
                select(PipelineModel).where(PipelineModel.id == pipeline_id)
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def _db_save_run(self, run: PipelineRun) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from backend.db.models import PipelineRunModel
        async with factory() as session:
            row = PipelineRunModel(
                id=run.run_id, pipeline_id=run.pipeline_id,
                pipeline_name=run.pipeline_name, status=run.status,
                pattern=run.pattern, steps_completed=run.steps_completed,
                steps_total=run.steps_total, step_results_json=run.step_results,
                input_data_json=run.input_data, output_data_json=run.output_data,
                started_at=run.started_at, completed_at=run.completed_at,
                total_latency_ms=run.total_latency_ms, total_cost=run.total_cost,
                error=run.error,
            )
            session.add(row)
            await session.commit()
            return True

    async def _db_stats(self) -> Dict[str, Any]:
        factory = self._sf()
        if not factory:
            return {}
        from sqlalchemy import select, func
        from backend.db.models import PipelineModel, PipelineRunModel
        async with factory() as session:
            total_pipes = (await session.execute(select(func.count(PipelineModel.id)))).scalar() or 0
            total_runs = (await session.execute(select(func.count(PipelineRunModel.id)))).scalar() or 0
            ok_runs = (await session.execute(
                select(func.count(PipelineRunModel.id)).where(PipelineRunModel.status == "completed")
            )).scalar() or 0
            return {
                "total_pipelines": total_pipes, "total_runs": total_runs,
                "successful_runs": ok_runs, "failed_runs": total_runs - ok_runs,
                "persistence": "postgresql",
            }

    # ── Pipeline CRUD ─────────────────────────────────────────────

    def create_pipeline(self, pipeline: Pipeline) -> Pipeline:
        pipeline.created_at = datetime.utcnow()
        pipeline.updated_at = datetime.utcnow()
        self._pipelines[pipeline.pipeline_id] = pipeline
        self._versions[pipeline.pipeline_id] = [copy.deepcopy(pipeline)]
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_create_pipeline(pipeline))
            except Exception:
                pass
        return pipeline

    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        return self._pipelines.get(pipeline_id)

    def update_pipeline(self, pipeline_id: str, updates: Dict[str, Any]) -> Optional[Pipeline]:
        pipe = self._pipelines.get(pipeline_id)
        if not pipe:
            return None
        for k, v in updates.items():
            if hasattr(pipe, k) and k not in ("pipeline_id", "created_at"):
                setattr(pipe, k, v)
        pipe.version += 1
        pipe.updated_at = datetime.utcnow()
        self._versions.setdefault(pipeline_id, []).append(copy.deepcopy(pipe))
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_update_pipeline(pipeline_id, updates))
            except Exception:
                pass
        return pipe

    def delete_pipeline(self, pipeline_id: str) -> bool:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_delete_pipeline(pipeline_id))
            except Exception:
                pass
        removed = self._pipelines.pop(pipeline_id, None)
        self._versions.pop(pipeline_id, None)
        return removed is not None

    def list_pipelines(self, status: Optional[str] = None) -> List[Pipeline]:
        pipes = list(self._pipelines.values())
        if status:
            pipes = [p for p in pipes if p.status == status]
        return sorted(pipes, key=lambda p: p.updated_at, reverse=True)

    def search_pipelines(self, query: str) -> List[Pipeline]:
        q = query.lower()
        return [
            p for p in self._pipelines.values()
            if q in p.name.lower() or q in p.description.lower()
        ]

    # ── Pipeline Execution ────────────────────────────────────────

    def execute_pipeline(
        self, pipeline_id: str, input_data: Dict[str, Any] = None,
    ) -> PipelineRun:
        """
        Synchronous wrapper around async execution.
        """
        from backend.db.sync_bridge import run_async
        try:
            return run_async(self.execute_pipeline_async(pipeline_id, input_data))
        except Exception:
            # Fallback if no event loop available
            import asyncio as _aio
            return _aio.run(self.execute_pipeline_async(pipeline_id, input_data))

    async def execute_pipeline_async(
        self, pipeline_id: str, input_data: Dict[str, Any] = None,
    ) -> PipelineRun:
        """
        Execute a pipeline with real async parallel support.
        Sequential steps run in order; parallel steps use asyncio.gather
        with bounded concurrency via a semaphore.
        """
        pipe = self._pipelines.get(pipeline_id)
        if not pipe:
            run = PipelineRun(
                pipeline_id=pipeline_id,
                status="failed",
                error=f"Pipeline '{pipeline_id}' not found",
            )
            self._runs.append(run)
            return run

        start = time.time()
        run = PipelineRun(
            pipeline_id=pipeline_id,
            pipeline_name=pipe.name,
            pattern=pipe.pattern.value,
            steps_total=len([s for s in pipe.steps if s.enabled]),
            input_data=input_data or {},
        )

        active_steps = [s for s in pipe.steps if s.enabled]
        active_steps.sort(key=lambda s: s.order)

        accumulated_state = dict(input_data or {})

        if pipe.pattern == OrchestrationPattern.SEQUENTIAL:
            for step in active_steps:
                step_result = await self._execute_step_async(step, accumulated_state)
                run.step_results.append(step_result)
                run.steps_completed += 1
                if step.output_key:
                    accumulated_state[step.output_key] = step_result.get("output")
                if step_result.get("status") == "failed":
                    run.status = "failed"
                    run.error = step_result.get("error")
                    break

        elif pipe.pattern == OrchestrationPattern.PARALLEL:
            # Real parallel execution with bounded concurrency
            async def _run_with_semaphore(step):
                async with _PARALLEL_SEMAPHORE:
                    return await asyncio.wait_for(
                        self._execute_step_async(step, accumulated_state),
                        timeout=step.timeout_seconds,
                    )

            tasks = [_run_with_semaphore(s) for s in active_steps]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for step, result in zip(active_steps, results):
                if isinstance(result, Exception):
                    step_result = {
                        "step_id": step.step_id, "agent_id": step.agent_id,
                        "agent_name": step.agent_name, "status": "failed",
                        "error": str(result), "latency_ms": 0, "tokens_used": 0,
                    }
                else:
                    step_result = result
                run.step_results.append(step_result)
                run.steps_completed += 1
                if step.output_key:
                    accumulated_state[step.output_key] = step_result.get("output")

        elif pipe.pattern == OrchestrationPattern.SUPERVISOR:
            supervisor_result = {
                "status": "completed",
                "agent_id": pipe.supervisor_agent_id,
                "message": "Supervisor delegated to spoke agents",
                "delegations": [s.agent_id for s in active_steps],
            }
            run.step_results.append(supervisor_result)
            # Spoke agents run in parallel under supervisor
            async def _run_spoke(step):
                async with _PARALLEL_SEMAPHORE:
                    return await self._execute_step_async(step, accumulated_state)

            spoke_results = await asyncio.gather(
                *[_run_spoke(s) for s in active_steps], return_exceptions=True
            )
            for step, result in zip(active_steps, spoke_results):
                step_result = result if not isinstance(result, Exception) else {
                    "step_id": step.step_id, "agent_id": step.agent_id,
                    "status": "failed", "error": str(result),
                }
                run.step_results.append(step_result)
                run.steps_completed += 1

        if run.status == "running":
            run.status = "completed"

        run.output_data = accumulated_state
        run.completed_at = datetime.utcnow()
        run.total_latency_ms = round((time.time() - start) * 1000, 1)
        self._runs.append(run)
        # Persist run to DB
        if self._db_available:
            try:
                await self._db_save_run(run)
            except Exception:
                pass
        return run

    async def _execute_step_async(self, step: PipelineStep, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single pipeline step (simulated in Phase 1, async-ready for Phase 2)."""
        # Simulate some async work
        await asyncio.sleep(0)
        return {
            "step_id": step.step_id,
            "agent_id": step.agent_id,
            "agent_name": step.agent_name,
            "status": "completed",
            "output": f"Result from agent '{step.agent_name or step.agent_id}'",
            "latency_ms": 150.0,
            "tokens_used": 500,
        }

    # ── Run History (DB-backed with in-memory fallback) ─────────

    async def _db_get_run(self, run_id: str) -> Optional[PipelineRun]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import PipelineRunModel
        async with factory() as session:
            row = (await session.execute(
                select(PipelineRunModel).where(PipelineRunModel.id == run_id)
            )).scalar_one_or_none()
            if not row:
                return None
            return self._row_to_run(row)

    async def _db_list_runs(self, pipeline_id: Optional[str], limit: int) -> List[PipelineRun]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import PipelineRunModel
        async with factory() as session:
            q = select(PipelineRunModel).order_by(PipelineRunModel.started_at.desc()).limit(limit)
            if pipeline_id:
                q = q.where(PipelineRunModel.pipeline_id == pipeline_id)
            rows = (await session.execute(q)).scalars().all()
            return [self._row_to_run(r) for r in rows]

    @staticmethod
    def _row_to_run(row) -> PipelineRun:
        return PipelineRun(
            run_id=row.id, pipeline_id=row.pipeline_id,
            pipeline_name=row.pipeline_name or "", status=row.status or "unknown",
            pattern=row.pattern or "", steps_completed=row.steps_completed or 0,
            steps_total=row.steps_total or 0,
            step_results=row.step_results_json or [],
            input_data=row.input_data_json or {},
            output_data=row.output_data_json or {},
            started_at=row.started_at or datetime.utcnow(),
            completed_at=row.completed_at,
            total_latency_ms=row.total_latency_ms or 0,
            total_cost=row.total_cost or 0,
            error=row.error,
        )

    def get_run(self, run_id: str) -> Optional[PipelineRun]:
        # Check in-memory first
        for r in self._runs:
            if r.run_id == run_id:
                return r
        # Fall back to DB
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_get_run(run_id))
            except Exception:
                pass
        return None

    def list_runs(self, pipeline_id: Optional[str] = None, limit: int = 20) -> List[PipelineRun]:
        # Use DB when available for durable history
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                db_runs = run_async(self._db_list_runs(pipeline_id, limit))
                if db_runs:
                    return db_runs
            except Exception:
                pass
        # Fall back to in-memory
        runs = self._runs
        if pipeline_id:
            runs = [r for r in runs if r.pipeline_id == pipeline_id]
        return sorted(runs, key=lambda r: r.started_at, reverse=True)[:limit]

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_stats())
                if result:
                    return result
            except Exception:
                pass
        pipes = list(self._pipelines.values())
        by_pattern: Dict[str, int] = {}
        for p in pipes:
            by_pattern[p.pattern.value] = by_pattern.get(p.pattern.value, 0) + 1
        return {
            "total_pipelines": len(pipes),
            "by_pattern": by_pattern,
            "total_runs": len(self._runs),
            "successful_runs": sum(1 for r in self._runs if r.status == "completed"),
            "failed_runs": sum(1 for r in self._runs if r.status == "failed"),
            "persistence": "in-memory",
        }
