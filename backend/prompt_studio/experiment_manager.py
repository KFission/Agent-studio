"""
JAI Agent OS — Langfuse-backed Experiment Manager
Manages datasets and experiment runs via Langfuse's REST API.
Supports: dataset CRUD, dataset items, experiment runs, run items.
"""

import httpx
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone


class ExperimentManager:
    """
    Manages experiments (datasets + runs) via Langfuse's REST API.
    An experiment runs a prompt version against a dataset of test cases.
    """

    def __init__(self, host: str, public_key: str, secret_key: str):
        self._host = host.rstrip("/")
        self._public_key = public_key
        self._secret_key = secret_key

    def _auth(self):
        return (self._public_key, self._secret_key)

    def _api(self, path: str) -> str:
        return f"{self._host}/api/public/v2{path}"

    def _api_v1(self, path: str) -> str:
        """Some endpoints (dataset-items, dataset-run-items) use /api/public/ without v2."""
        return f"{self._host}/api/public{path}"

    # ── Datasets ────────────────────────────────────────────────────────

    def list_datasets(self, limit: int = 50, page: int = 1) -> Dict:
        """List all datasets."""
        try:
            resp = httpx.get(self._api("/datasets"), auth=self._auth(),
                             params={"limit": limit, "page": page}, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[EXPERIMENT] list datasets error: {e}")
        return {"data": []}

    def get_dataset(self, name: str) -> Optional[Dict]:
        """Get a dataset by name."""
        try:
            resp = httpx.get(self._api(f"/datasets/{name}"), auth=self._auth(), timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[EXPERIMENT] get dataset error: {e}")
        return None

    def create_dataset(self, name: str, description: str = "", metadata: Optional[Dict] = None) -> Optional[Dict]:
        """Create a new dataset."""
        body = {"name": name}
        if description:
            body["description"] = description
        if metadata:
            body["metadata"] = metadata
        try:
            resp = httpx.post(self._api("/datasets"), auth=self._auth(), json=body, timeout=10)
            if resp.status_code in (200, 201):
                return resp.json()
            print(f"[EXPERIMENT] create dataset error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[EXPERIMENT] create dataset error: {e}")
        return None

    # ── Dataset Items ───────────────────────────────────────────────────

    def create_dataset_item(self, dataset_name: str, input_data: Any,
                            expected_output: Any = None, metadata: Optional[Dict] = None) -> Optional[Dict]:
        """Add a test case to a dataset."""
        body: Dict[str, Any] = {
            "datasetName": dataset_name,
            "input": input_data,
        }
        if expected_output is not None:
            body["expectedOutput"] = expected_output
        if metadata:
            body["metadata"] = metadata
        try:
            resp = httpx.post(self._api_v1("/dataset-items"), auth=self._auth(), json=body, timeout=10)
            if resp.status_code in (200, 201):
                return resp.json()
            print(f"[EXPERIMENT] create item error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[EXPERIMENT] create item error: {e}")
        return None

    def get_dataset_items(self, dataset_name: str, limit: int = 50, page: int = 1) -> List[Dict]:
        """Get items in a dataset via the dataset-items endpoint."""
        try:
            resp = httpx.get(self._api_v1("/dataset-items"),
                             auth=self._auth(),
                             params={"datasetName": dataset_name, "limit": limit, "page": page},
                             timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", [])
        except Exception as e:
            print(f"[EXPERIMENT] get items error: {e}")
        return []

    # ── Dataset Runs ────────────────────────────────────────────────────

    def get_dataset_runs(self, dataset_name: str) -> List[Dict]:
        """Get all runs for a dataset."""
        try:
            resp = httpx.get(self._api_v1(f"/datasets/{dataset_name}/runs"),
                             auth=self._auth(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", [])
        except Exception as e:
            print(f"[EXPERIMENT] get runs error: {e}")
        return []

    def create_run_item(self, dataset_name: str, dataset_item_id: str,
                        trace_id: str, run_name: str,
                        observation_id: Optional[str] = None) -> Optional[Dict]:
        """Link a trace/observation to a dataset item as part of a run."""
        body: Dict[str, Any] = {
            "datasetItemId": dataset_item_id,
            "traceId": trace_id,
            "runName": run_name,
        }
        if observation_id:
            body["observationId"] = observation_id
        try:
            resp = httpx.post(self._api_v1("/dataset-run-items"), auth=self._auth(),
                              json=body, timeout=10)
            if resp.status_code in (200, 201):
                return resp.json()
            print(f"[EXPERIMENT] create run item error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[EXPERIMENT] create run item error: {e}")
        return None

    # ── High-level: Run Experiment ──────────────────────────────────────

    def run_experiment(
        self,
        dataset_name: str,
        prompt_name: str,
        prompt_version: int,
        model_id: str,
        run_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        prompt_manager=None,
        langfuse_manager=None,
        provider_factory=None,
        model_library=None,
        integration_manager=None,
        scoring_enabled: bool = True,
        scoring_metrics: Optional[List[str]] = None,
        llm_judge_enabled: bool = False,
        judge_model_id: str = "gemini-2.5-flash",
    ) -> Dict:
        """
        Run an experiment: execute a prompt against all items in a dataset.
        Returns a summary of the run.
        """
        import time as _time

        if not run_name:
            run_name = f"{prompt_name}-v{prompt_version}-{model_id}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        # Get prompt
        prompt_data = prompt_manager.get_prompt(prompt_name, version=prompt_version) if prompt_manager else None
        if not prompt_data:
            return {"error": f"Prompt '{prompt_name}' v{prompt_version} not found"}

        prompt_content = prompt_data.get("prompt", "")
        prompt_type = prompt_data.get("type", "text")

        # Get dataset items
        items = self.get_dataset_items(dataset_name)
        if not items:
            return {"error": f"Dataset '{dataset_name}' has no items"}

        # Resolve model credentials
        extra_kwargs = {}
        credential_data = None
        if model_library and integration_manager:
            model_entry = model_library.get(model_id)
            if model_entry:
                intg_id = (model_entry.metadata or {}).get("integration_id")
                if intg_id:
                    intg = integration_manager.get(intg_id)
                    if intg:
                        if intg.auth_type == "api_key" and intg.api_key:
                            extra_kwargs["google_api_key"] = intg.api_key
                        elif intg.auth_type == "service_account" and intg.service_account_json:
                            credential_data = intg.service_account_json

        # Create LLM
        llm = None
        if provider_factory:
            llm = provider_factory.create(
                model_id, temperature=temperature, max_tokens=max_tokens,
                credential_data=credential_data, **extra_kwargs,
            )

        results = []
        for item in items:
            item_id = item.get("id")
            input_data = item.get("input", {})
            expected = item.get("expectedOutput")

            # Build variables from input
            variables = input_data if isinstance(input_data, dict) else {}

            # Render prompt
            from backend.prompt_studio.langfuse_prompt_manager import LangfusePromptManager
            rendered = LangfusePromptManager.render_prompt(prompt_content, variables)

            # Build messages
            if isinstance(rendered, str):
                messages = [{"role": "user", "content": rendered}]
            elif isinstance(rendered, list):
                messages = rendered
            else:
                messages = [{"role": "user", "content": str(rendered)}]

            # Create trace
            trace_id = None
            if langfuse_manager:
                trace_id = langfuse_manager.create_trace(
                    name=f"experiment-{run_name}",
                    metadata={"prompt_name": prompt_name, "prompt_version": prompt_version,
                              "dataset": dataset_name, "model": model_id, "run_name": run_name},
                    tags=["experiment", model_id, dataset_name],
                )

            # Run LLM
            start = _time.time()
            output = ""
            error_msg = None
            input_tokens = 0
            output_tokens = 0
            try:
                if llm:
                    response = llm.invoke(messages)
                    output = response.content if hasattr(response, "content") else str(response)
                    usage = getattr(response, "usage_metadata", None)
                    input_tokens = usage.get("input_tokens", 0) if isinstance(usage, dict) else 0
                    output_tokens = usage.get("output_tokens", 0) if isinstance(usage, dict) else 0
                else:
                    output = "[No LLM configured]"
            except Exception as e:
                error_msg = str(e)
                output = f"[Error: {e}]"
            latency_ms = (_time.time() - start) * 1000

            # Log generation
            if langfuse_manager and trace_id:
                langfuse_manager.log_generation(
                    trace_id=trace_id, name="experiment-generation", model=model_id,
                    input={"messages": messages}, output={"content": output},
                    usage={"input": input_tokens, "output": output_tokens,
                           "total": input_tokens + output_tokens, "unit": "TOKENS"},
                    metadata={"latency_ms": round(latency_ms, 1), "run_name": run_name},
                    end_time=datetime.now(timezone.utc).isoformat(),
                )
                langfuse_manager.update_trace(trace_id, output={"content": output[:300]})

            # Link trace to dataset item
            if trace_id and item_id:
                self.create_run_item(dataset_name, item_id, trace_id, run_name)

            # Auto-score if expected output exists
            scores = None
            if scoring_enabled and expected and not error_msg:
                try:
                    from backend.eval_studio.scoring import score_output, EvalScoreRequest
                    score_req = EvalScoreRequest(
                        input_text=str(input_data) if isinstance(input_data, dict) else input_data,
                        output_text=output,
                        reference_text=str(expected) if not isinstance(expected, str) else expected,
                        metrics=scoring_metrics or ["exact_match", "contains", "rouge_l", "bleu"],
                        llm_judge_enabled=llm_judge_enabled,
                        judge_model_id=judge_model_id,
                    )
                    score_resp = score_output(score_req, provider_factory=provider_factory)
                    scores = {
                        "aggregate_score": score_resp.aggregate_score,
                        "reference_scores": [
                            {"metric": s.metric, "score": s.score, "reasoning": s.reasoning}
                            for s in score_resp.reference_scores
                        ],
                        "summary": score_resp.summary,
                    }
                    if score_resp.judge_result and not score_resp.judge_result.error:
                        scores["judge"] = {
                            "overall_score": score_resp.judge_result.overall_score,
                            "criteria_scores": score_resp.judge_result.criteria_scores,
                            "reasoning": score_resp.judge_result.overall_reasoning,
                        }
                except Exception as e:
                    scores = {"error": str(e)}

            results.append({
                "item_id": item_id,
                "input": input_data,
                "expected_output": expected,
                "output": output,
                "error": error_msg,
                "latency_ms": round(latency_ms, 1),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "trace_id": trace_id,
                "scores": scores,
            })

        # Compute aggregate scores across all items
        scored_items = [r for r in results if r.get("scores") and "aggregate_score" in r["scores"]]
        avg_score = (sum(r["scores"]["aggregate_score"] for r in scored_items) / len(scored_items)) if scored_items else None

        return {
            "run_name": run_name,
            "dataset_name": dataset_name,
            "prompt_name": prompt_name,
            "prompt_version": prompt_version,
            "model_id": model_id,
            "total_items": len(items),
            "completed": len([r for r in results if not r.get("error")]),
            "errors": len([r for r in results if r.get("error")]),
            "scoring": {
                "enabled": scoring_enabled,
                "items_scored": len(scored_items),
                "average_score": round(avg_score, 4) if avg_score is not None else None,
                "llm_judge_enabled": llm_judge_enabled,
            },
            "results": results,
        }
