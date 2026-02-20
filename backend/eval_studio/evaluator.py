"""
Evaluation Studio - Test prompts against multiple models, estimate tokens,
calculate cost per LLM, and benchmark latency.
Enables side-by-side model comparison from the Agent Studio UI.
"""

import time
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from backend.llm_registry.model_library import ModelLibrary, ModelEntry
from backend.llm_registry.provider_factory import ProviderFactory


class EvalStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvalResult(BaseModel):
    """Result of evaluating a single prompt against a single model."""
    model_id: str
    model_name: str
    provider: str
    response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    tokens_per_second: float = 0.0
    status: EvalStatus = EvalStatus.PENDING
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Quality scoring fields
    quality_scores: Optional[Dict[str, Any]] = None


class EvalRun(BaseModel):
    """A complete evaluation run testing a prompt across multiple models."""
    run_id: str = Field(default_factory=lambda: f"EVAL-{uuid.uuid4().hex[:8].upper()}")
    prompt: str
    variables: Dict[str, str] = Field(default_factory=dict)
    rendered_prompt: str = ""
    model_ids: List[str] = Field(default_factory=list)
    results: List[EvalResult] = Field(default_factory=list)
    status: EvalStatus = EvalStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    created_by: str = "user"

    @property
    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self.results)

    @property
    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.results)

    @property
    def fastest_model(self) -> Optional[str]:
        completed = [r for r in self.results if r.status == EvalStatus.COMPLETED]
        if not completed:
            return None
        return min(completed, key=lambda r: r.latency_ms).model_id

    @property
    def cheapest_model(self) -> Optional[str]:
        completed = [r for r in self.results if r.status == EvalStatus.COMPLETED]
        if not completed:
            return None
        return min(completed, key=lambda r: r.cost_usd).model_id


# ── Token Estimation ──────────────────────────────────────────────────────────

def estimate_tokens(text: str, method: str = "chars") -> int:
    """
    Estimate token count for a text string.
    Uses character-based heuristic (1 token ~ 4 chars for English).
    For precise counts, use tiktoken or model-specific tokenizers.
    """
    if method == "words":
        return int(len(text.split()) * 1.3)
    # chars method: ~4 chars per token
    return max(1, len(text) // 4)


def estimate_cost_for_prompt(
    prompt: str,
    model_library: ModelLibrary,
    expected_output_tokens: int = 500,
) -> List[Dict[str, Any]]:
    """
    Estimate the cost of running a prompt across all available models.
    Returns sorted list from cheapest to most expensive.
    """
    input_tokens = estimate_tokens(prompt)
    return model_library.compare_costs(input_tokens, expected_output_tokens)


# ── Evaluation Studio ─────────────────────────────────────────────────────────

class EvaluationStudio:
    """
    Test prompts against multiple LLM models, measure latency, tokens, and cost.
    Provides side-by-side comparison for model selection decisions.
    """

    def __init__(
        self,
        library: Optional[ModelLibrary] = None,
        factory: Optional[ProviderFactory] = None,
        integration_manager=None,
    ):
        self._library = library or ModelLibrary()
        self._factory = factory or ProviderFactory(self._library)
        self._integration_manager = integration_manager
        self._runs: Dict[str, EvalRun] = {}

    def _resolve_credentials(self, model_id: str):
        """Resolve integration credentials for a model (api_key or service_account)."""
        extra_kwargs = {}
        credential_data = None
        model = self._library.get(model_id)
        if model and self._integration_manager:
            intg_id = (model.metadata or {}).get("integration_id")
            if intg_id:
                intg = self._integration_manager.get(intg_id)
                if intg:
                    if intg.auth_type == "api_key" and intg.api_key:
                        extra_kwargs["google_api_key"] = intg.api_key
                    elif intg.auth_type == "service_account" and intg.service_account_json:
                        credential_data = intg.service_account_json
        return extra_kwargs, credential_data

    def estimate_tokens(self, text: str) -> Dict[str, Any]:
        """Estimate token count and cost across all models."""
        token_count = estimate_tokens(text)
        costs = estimate_cost_for_prompt(text, self._library)
        return {
            "text_length": len(text),
            "estimated_tokens": token_count,
            "cost_estimates": costs,
        }

    def evaluate_single(
        self,
        prompt: str,
        model_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reference_text: Optional[str] = None,
        scoring_metrics: Optional[List[str]] = None,
        llm_judge_enabled: bool = False,
        judge_model_id: str = "gemini-2.5-flash",
        judge_criteria: Optional[List[str]] = None,
    ) -> EvalResult:
        """Evaluate a prompt against a single model."""
        model = self._library.get(model_id)
        if not model:
            return EvalResult(
                model_id=model_id,
                model_name="unknown",
                provider="unknown",
                status=EvalStatus.FAILED,
                error=f"Model '{model_id}' not found",
            )

        result = EvalResult(
            model_id=model_id,
            model_name=model.display_name,
            provider=model.provider.value,
            status=EvalStatus.RUNNING,
        )

        try:
            extra_kwargs, credential_data = self._resolve_credentials(model_id)
            llm = self._factory.create(
                model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                credential_data=credential_data,
                **extra_kwargs,
            )

            start = time.time()
            response = llm.invoke(prompt)
            latency_ms = (time.time() - start) * 1000

            content = response.content if hasattr(response, "content") else str(response)
            usage = getattr(response, "usage_metadata", None)

            # usage_metadata can be a dict (Google) or object (Anthropic/OpenAI)
            if isinstance(usage, dict):
                input_tokens = usage.get("input_tokens", 0) or 0
                output_tokens = usage.get("output_tokens", 0) or 0
            elif usage:
                input_tokens = getattr(usage, "input_tokens", 0) or 0
                output_tokens = getattr(usage, "output_tokens", 0) or 0
            else:
                input_tokens = 0
                output_tokens = 0
            # Fall back to estimation when provider doesn't report tokens
            if input_tokens == 0:
                input_tokens = estimate_tokens(prompt)
            if output_tokens == 0:
                output_tokens = estimate_tokens(content)

            result.response = content
            result.input_tokens = input_tokens
            result.output_tokens = output_tokens
            result.total_tokens = input_tokens + output_tokens
            result.latency_ms = round(latency_ms, 1)
            result.cost_usd = round(model.pricing.estimate_cost(input_tokens, output_tokens), 6)
            result.tokens_per_second = round(output_tokens / (latency_ms / 1000), 1) if latency_ms > 0 else 0
            result.status = EvalStatus.COMPLETED

        except Exception as e:
            result.status = EvalStatus.FAILED
            result.error = str(e)

        # Quality scoring — run if we have a completed response
        if result.status == EvalStatus.COMPLETED and (reference_text or llm_judge_enabled):
            try:
                from backend.eval_studio.scoring import score_output, EvalScoreRequest
                score_req = EvalScoreRequest(
                    input_text=prompt,
                    output_text=result.response,
                    reference_text=reference_text,
                    metrics=scoring_metrics or ["exact_match", "contains", "rouge_l", "bleu"],
                    llm_judge_enabled=llm_judge_enabled,
                    judge_model_id=judge_model_id,
                    judge_criteria=judge_criteria,
                )
                score_resp = score_output(score_req, provider_factory=self._factory)
                quality = {
                    "aggregate_score": score_resp.aggregate_score,
                    "summary": score_resp.summary,
                    "reference_scores": [
                        {"metric": s.metric, "score": s.score, "reasoning": s.reasoning}
                        for s in score_resp.reference_scores
                    ],
                }
                if score_resp.judge_result and not score_resp.judge_result.error:
                    quality["judge"] = {
                        "overall_score": score_resp.judge_result.overall_score,
                        "criteria_scores": score_resp.judge_result.criteria_scores,
                        "reasoning": score_resp.judge_result.overall_reasoning,
                        "model": score_resp.judge_result.judge_model,
                        "latency_ms": score_resp.judge_result.latency_ms,
                    }
                elif score_resp.judge_result and score_resp.judge_result.error:
                    quality["judge_error"] = score_resp.judge_result.error
                result.quality_scores = quality
            except Exception as e:
                result.quality_scores = {"error": str(e)}

        return result

    def evaluate_multi(
        self,
        prompt: str,
        model_ids: List[str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        created_by: str = "user",
        reference_text: Optional[str] = None,
        scoring_metrics: Optional[List[str]] = None,
        llm_judge_enabled: bool = False,
        judge_model_id: str = "gemini-2.5-flash",
        judge_criteria: Optional[List[str]] = None,
    ) -> EvalRun:
        """
        Evaluate a prompt against multiple models for side-by-side comparison.
        Returns an EvalRun with results for each model.
        """
        run = EvalRun(
            prompt=prompt,
            rendered_prompt=prompt,
            model_ids=model_ids,
            status=EvalStatus.RUNNING,
            created_by=created_by,
        )

        for model_id in model_ids:
            result = self.evaluate_single(
                prompt, model_id, temperature, max_tokens,
                reference_text=reference_text,
                scoring_metrics=scoring_metrics,
                llm_judge_enabled=llm_judge_enabled,
                judge_model_id=judge_model_id,
                judge_criteria=judge_criteria,
            )
            run.results.append(result)

        run.status = EvalStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        self._runs[run.run_id] = run
        return run

    def get_run(self, run_id: str) -> Optional[EvalRun]:
        return self._runs.get(run_id)

    def list_runs(self, limit: int = 50) -> List[EvalRun]:
        runs = sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)
        return runs[:limit]

    def get_comparison_table(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get a formatted comparison table for a run."""
        run = self.get_run(run_id)
        if not run:
            return None

        return {
            "run_id": run.run_id,
            "prompt_preview": run.prompt[:100] + "..." if len(run.prompt) > 100 else run.prompt,
            "models_tested": len(run.results),
            "total_cost": round(run.total_cost, 6),
            "total_tokens": run.total_tokens,
            "fastest_model": run.fastest_model,
            "cheapest_model": run.cheapest_model,
            "results": [
                {
                    "model_id": r.model_id,
                    "model_name": r.model_name,
                    "provider": r.provider,
                    "status": r.status.value,
                    "latency_ms": r.latency_ms,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost_usd": r.cost_usd,
                    "tokens_per_second": r.tokens_per_second,
                    "response_preview": r.response[:200] if r.response else "",
                    "error": r.error,
                    "quality_scores": r.quality_scores,
                }
                for r in run.results
            ],
        }
