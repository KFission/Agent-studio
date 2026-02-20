"""
JAI Agent OS — V4 API Routes
Groups (LoB/Teams), Model-Group Assignment, Usage Metering & Cost Reports, LLM Integrations
"""

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Header
from pydantic import BaseModel, Field


# ── Request Models ────────────────────────────────────────────────

class CreateGroupRequest(BaseModel):
    name: str
    description: str = ""
    lob: str = ""
    allowed_model_ids: List[str] = Field(default_factory=list)
    allowed_agent_ids: List[str] = Field(default_factory=list)
    assigned_roles: List[str] = Field(default_factory=lambda: ["agent_developer"])
    monthly_budget_usd: float = 0

class UpdateGroupRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    lob: Optional[str] = None
    is_active: Optional[bool] = None
    monthly_budget_usd: Optional[float] = None

class AssignModelsRequest(BaseModel):
    model_ids: List[str]

class AssignAgentsRequest(BaseModel):
    agent_ids: List[str]

class AssignRolesRequest(BaseModel):
    roles: List[str]

class AddMemberRequest(BaseModel):
    user_id: str

class CreateIntegrationRequest(BaseModel):
    name: str
    provider: str
    api_key: str = ""
    auth_type: str = "api_key"  # api_key | service_account
    service_account_json: Optional[Dict[str, Any]] = None
    description: str = ""
    endpoint_url: str = ""
    project_id: str = ""
    default_model: str = ""
    allowed_models: List[str] = Field(default_factory=list)
    registered_models: List[str] = Field(default_factory=list)
    rate_limit_rpm: int = 0
    assigned_group_ids: List[str] = Field(default_factory=list)

class UpdateIntegrationRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    api_key: Optional[str] = None
    auth_type: Optional[str] = None
    service_account_json: Optional[Dict[str, Any]] = None
    endpoint_url: Optional[str] = None
    project_id: Optional[str] = None
    default_model: Optional[str] = None
    registered_models: Optional[List[str]] = None
    rate_limit_rpm: Optional[int] = None
    status: Optional[str] = None

class PushIntegrationRequest(BaseModel):
    group_ids: List[str]

class InvokeAgentRequest(BaseModel):
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False

class InvokeWorkflowRequest(BaseModel):
    input_data: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""

class CreateTokenRequest(BaseModel):
    name: str = "My API Token"


def register_v4_routes(app: FastAPI, group_manager, usage_metering, model_library=None, integration_manager=None, agent_registry=None, orchestrator=None, gateway=None, llm_log_manager=None, api_token_store=None, guardrail_manager=None):
    """Register Group Management, Usage Metering, Guardrails, and Dashboard routes."""

    # ══════════════════════════════════════════════════════════════
    # GUARDRAILS
    # ══════════════════════════════════════════════════════════════

    @app.get("/guardrails", tags=["Guardrails"])
    async def list_guardrails():
        if not guardrail_manager:
            return {"count": 0, "rules": []}
        rules = guardrail_manager.list_all()
        return {"count": len(rules), "rules": [r.model_dump(mode="json") for r in rules]}

    @app.get("/guardrails/stats", tags=["Guardrails"])
    async def guardrails_stats():
        if not guardrail_manager:
            return {}
        return guardrail_manager.get_stats()

    @app.get("/guardrails/{rule_id}", tags=["Guardrails"])
    async def get_guardrail(rule_id: str):
        if not guardrail_manager:
            raise HTTPException(404, "Guardrails not configured")
        rule = guardrail_manager.get(rule_id)
        if not rule:
            raise HTTPException(404, "Rule not found")
        return rule.model_dump(mode="json")

    @app.post("/guardrails", tags=["Guardrails"])
    async def create_guardrail(req: dict):
        if not guardrail_manager:
            raise HTTPException(500, "Guardrails not configured")
        rule = await guardrail_manager.create_async(
            name=req.get("name", "Untitled Rule"),
            description=req.get("description", ""),
            rule_type=req.get("rule_type", "custom"),
            scope=req.get("scope", "global"),
            action=req.get("action", "block"),
            applies_to=req.get("applies_to", "both"),
            config=req.get("config", {}),
            agent_ids=req.get("agent_ids", []),
            group_ids=req.get("group_ids", []),
        )
        return {"status": "created", "rule_id": rule.rule_id}

    @app.put("/guardrails/{rule_id}", tags=["Guardrails"])
    async def update_guardrail(rule_id: str, req: dict):
        if not guardrail_manager:
            raise HTTPException(500, "Guardrails not configured")
        rule = await guardrail_manager.update_async(rule_id, req)
        if not rule:
            raise HTTPException(404, "Rule not found")
        return {"status": "updated", "rule_id": rule.rule_id}

    @app.delete("/guardrails/{rule_id}", tags=["Guardrails"])
    async def delete_guardrail(rule_id: str):
        if not guardrail_manager:
            raise HTTPException(500, "Guardrails not configured")
        if not await guardrail_manager.delete_async(rule_id):
            raise HTTPException(404, "Rule not found")
        return {"status": "deleted"}

    @app.get("/guardrails/agent/{agent_id}", tags=["Guardrails"])
    async def guardrails_for_agent(agent_id: str):
        if not guardrail_manager:
            return {"count": 0, "rules": []}
        rules = guardrail_manager.get_rules_for_agent(agent_id)
        return {"count": len(rules), "rules": [r.model_dump(mode="json") for r in rules]}

    # ══════════════════════════════════════════════════════════════
    # GUARDRAILS AI SERVICE (deploy/undeploy/validate via guardrails-api)
    # ══════════════════════════════════════════════════════════════

    from backend.guardrails.guardrails_client import guardrails_client, VALIDATOR_MAP, PROMPT_INJECTION_REGEX

    @app.get("/guardrails-ai/status", tags=["Guardrails"])
    async def guardrails_ai_status():
        """Check if the Guardrails AI service is running and list deployed guards."""
        health = await guardrails_client.health()
        deployed = []
        if health["status"] == "healthy":
            deployed = await guardrails_client.list_guards()
        return {
            "service": health,
            "deployed_guards": deployed,
            "deployed_count": len(deployed),
            "available_validators": list(VALIDATOR_MAP.keys()),
        }

    @app.post("/guardrails-ai/deploy", tags=["Guardrails"])
    async def deploy_guard_to_service(req: dict):
        """Deploy a guard definition to the Guardrails AI server."""
        guard_name = req.get("guard_name") or req.get("name")
        guard_type = req.get("guard_type") or req.get("rule_type")
        if not guard_name or not guard_type:
            raise HTTPException(400, "guard_name and guard_type are required")
        result = await guardrails_client.deploy_guard(
            guard_name=guard_name,
            guard_type=guard_type,
            description=req.get("description", ""),
            config=req.get("config", {}),
        )
        if "error" in result:
            raise HTTPException(400, result["error"])

        # Mark the rule as deployed (cache + DB)
        if guardrail_manager:
            for rule in guardrail_manager.list_all():
                if rule.name == guard_name or rule.rule_id == req.get("rule_id"):
                    await guardrail_manager.update_async(rule.rule_id, {"is_deployed": True})
                    break
        return result

    @app.post("/guardrails-ai/undeploy", tags=["Guardrails"])
    async def undeploy_guard_from_service(req: dict):
        """Remove a guard from the Guardrails AI server (saves resources)."""
        guard_name = req.get("guard_name") or req.get("name")
        if not guard_name:
            raise HTTPException(400, "guard_name is required")
        result = await guardrails_client.undeploy_guard(guard_name)
        if "error" in result:
            raise HTTPException(400, result["error"])

        # Mark as undeployed (cache + DB)
        if guardrail_manager:
            for rule in guardrail_manager.list_all():
                if rule.name == guard_name or rule.rule_id == req.get("rule_id"):
                    await guardrail_manager.update_async(rule.rule_id, {"is_deployed": False})
                    break
        return result

    @app.post("/guardrails-ai/validate", tags=["Guardrails"])
    async def validate_with_guard(req: dict):
        """Run text through a deployed guard for validation."""
        guard_name = req.get("guard_name")
        text = req.get("text") or req.get("input")
        if not guard_name or not text:
            raise HTTPException(400, "guard_name and text are required")
        result = await guardrails_client.validate(guard_name, text, req.get("metadata"))
        return result

    @app.get("/guardrails-ai/validators", tags=["Guardrails"])
    async def list_available_validators():
        """List pre-installed validators available for guard creation."""
        return {
            "validators": [
                {"id": k, "hub_package": v, "description": f"{k.replace('_', ' ').title()} validator"}
                for k, v in VALIDATOR_MAP.items()
            ]
        }

    @app.post("/guardrails-ai/test", tags=["Guardrails"])
    async def test_guard_adhoc(req: dict):
        """
        Ad-hoc test: run validation directly in Python for instant feedback.
        No guard deployment needed — ideal for testing custom configs.
        """
        import re
        guard_type = req.get("guard_type")
        text = req.get("text", "")
        config = req.get("config", {})
        if not guard_type or not text:
            raise HTTPException(400, "guard_type and text are required")

        result = {"guard_type": guard_type, "test_input": text, "config_used": config}

        if guard_type == "prompt_injection":
            extra = config.get("additional_patterns", [])
            base_regex = PROMPT_INJECTION_REGEX
            if extra:
                joined = "|".join(re.escape(p) if not any(c in p for c in r".*+?[](){}|\\^$") else p for p in extra)
                base_regex = f"{base_regex}|(?i)({joined})"
            match = re.search(base_regex, text)
            result["validation_passed"] = match is None
            result["matched_pattern"] = match.group(0) if match else None
            result["detail"] = "Prompt injection detected" if match else "Input is clean"

        elif guard_type == "regex_match":
            pattern = config.get("regex", "")
            if not pattern:
                return {**result, "validation_passed": True, "detail": "No regex pattern provided"}
            match = re.search(pattern, text)
            result["validation_passed"] = match is None
            result["matched_pattern"] = match.group(0) if match else None
            result["detail"] = f"Sensitive pattern found: '{match.group(0)}'" if match else "No sensitive patterns found"

        elif guard_type == "profanity":
            try:
                from better_profanity import profanity
                profanity.load_censor_words()
                has_profanity = profanity.contains_profanity(text)
                censored = profanity.censor(text) if has_profanity else text
                result["validation_passed"] = not has_profanity
                result["censored_output"] = censored
                result["detail"] = "Profanity detected" if has_profanity else "Text is clean"
            except ImportError:
                words = {"damn", "hell", "shit", "fuck", "ass", "bitch", "crap", "bastard"}
                found = [w for w in words if w in text.lower()]
                result["validation_passed"] = len(found) == 0
                result["found_words"] = found
                result["detail"] = f"Profanity detected: {found}" if found else "Text is clean"

        elif guard_type == "pii_detection":
            entities = config.get("pii_entities", ["EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "CREDIT_CARD"])
            found_pii = []
            pii_patterns = {
                "EMAIL_ADDRESS": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "PHONE_NUMBER": r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
                "US_SSN": r"\b\d{3}-\d{2}-\d{4}\b",
                "CREDIT_CARD": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
                "IP_ADDRESS": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
                "IBAN_CODE": r"\b[A-Z]{2}\d{2}\s?[\dA-Z]{4}\s?[\dA-Z]{4}\s?[\dA-Z]{4}(?:\s?[\dA-Z]{4}){0,4}\b",
            }
            for ent in entities:
                pat = pii_patterns.get(ent)
                if pat:
                    matches = re.findall(pat, text)
                    if matches:
                        found_pii.extend([{"entity": ent, "value": m} for m in matches])
            result["validation_passed"] = len(found_pii) == 0
            result["found_pii"] = found_pii
            result["detail"] = f"Found {len(found_pii)} PII items" if found_pii else "No PII detected"

        elif guard_type == "valid_length":
            min_len = config.get("min", 1)
            max_len = config.get("max", 10000)
            length = len(text)
            passed = min_len <= length <= max_len
            result["validation_passed"] = passed
            result["length"] = length
            result["detail"] = f"Length {length} is {'within' if passed else 'outside'} range [{min_len}, {max_len}]"

        elif guard_type == "reading_time":
            max_minutes = config.get("reading_time", 5)
            word_count = len(text.split())
            minutes = round(word_count / 200, 1)
            passed = minutes <= max_minutes
            result["validation_passed"] = passed
            result["word_count"] = word_count
            result["estimated_minutes"] = minutes
            result["detail"] = f"~{minutes} min read ({word_count} words) — {'OK' if passed else f'exceeds {max_minutes} min limit'}"

        else:
            result["validation_passed"] = True
            result["detail"] = f"No test logic for guard type: {guard_type}"

        return result

    @app.get("/guardrails-ai/defaults/{guard_type}", tags=["Guardrails"])
    async def get_guard_defaults(guard_type: str):
        """Return the default config for a guard type (useful for the test UI)."""
        defaults = {
            "pii_detection": {"pii_entities": ["EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "CREDIT_CARD", "IP_ADDRESS", "IBAN_CODE"]},
            "prompt_injection": {"regex": PROMPT_INJECTION_REGEX, "additional_patterns": []},
            "profanity": {},
            "regex_match": {"regex": ""},
            "valid_length": {"min": 1, "max": 10000},
            "reading_time": {"reading_time": 5},
        }
        if guard_type not in defaults:
            raise HTTPException(404, f"Unknown guard type: {guard_type}")
        return {"guard_type": guard_type, "default_config": defaults[guard_type]}

    # ══════════════════════════════════════════════════════════════
    # GROUPS (LoB / Teams)
    # ══════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════
    # DASHBOARD METRICS (CXO-level aggregations)
    # ══════════════════════════════════════════════════════════════

    @app.get("/dashboard/metrics", tags=["System"])
    async def dashboard_metrics(period_days: int = Query(default=30)):
        from collections import Counter, defaultdict
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        prev_cutoff = cutoff - timedelta(days=period_days)

        records = [r for r in usage_metering._records if r.timestamp and r.timestamp.replace(tzinfo=timezone.utc if r.timestamp.tzinfo is None else r.timestamp.tzinfo) >= cutoff]
        prev_records = [r for r in usage_metering._records if r.timestamp and prev_cutoff <= r.timestamp.replace(tzinfo=timezone.utc if r.timestamp.tzinfo is None else r.timestamp.tzinfo) < cutoff]

        # ── KPI summary ────────────────────────────────────────────
        total_calls = len(records)
        total_cost = sum(r.cost_usd for r in records)
        total_tokens = sum((r.input_tokens or 0) + (r.output_tokens or 0) for r in records)
        success_count = sum(1 for r in records if r.status == "success")
        success_rate = round((success_count / total_calls * 100), 1) if total_calls > 0 else 0
        avg_latency = round(sum(r.latency_ms for r in records) / total_calls, 1) if total_calls > 0 else 0
        avg_cost_per_call = round(total_cost / total_calls, 6) if total_calls > 0 else 0

        prev_cost = sum(r.cost_usd for r in prev_records)
        prev_calls = len(prev_records)
        cost_trend_pct = round(((total_cost - prev_cost) / prev_cost * 100), 1) if prev_cost > 0 else 0
        calls_trend_pct = round(((total_calls - prev_calls) / prev_calls * 100), 1) if prev_calls > 0 else 0

        # ── Top agents by usage ────────────────────────────────────
        agent_usage = defaultdict(lambda: {"calls": 0, "cost": 0, "tokens": 0, "success": 0})
        for r in records:
            a = agent_usage[r.agent_id]
            a["calls"] += 1
            a["cost"] += r.cost_usd
            a["tokens"] += (r.input_tokens or 0) + (r.output_tokens or 0)
            if r.status == "success":
                a["success"] += 1
        agent_names = {}
        if agent_registry:
            for aid in agent_usage:
                ag = agent_registry.get(aid)
                agent_names[aid] = ag.name if ag else aid
        top_agents = sorted(
            [{"agent_id": k, "agent_name": agent_names.get(k, k), "calls": v["calls"], "cost_usd": round(v["cost"], 4), "tokens": v["tokens"], "success_rate": round(v["success"] / v["calls"] * 100, 1) if v["calls"] > 0 else 0} for k, v in agent_usage.items()],
            key=lambda x: x["calls"], reverse=True,
        )[:10]

        # ── Top models by cost ─────────────────────────────────────
        model_usage = defaultdict(lambda: {"calls": 0, "cost": 0, "tokens": 0})
        for r in records:
            m = model_usage[r.model_id]
            m["calls"] += 1
            m["cost"] += r.cost_usd
            m["tokens"] += (r.input_tokens or 0) + (r.output_tokens or 0)
        top_models = sorted(
            [{"model": k, "calls": v["calls"], "cost_usd": round(v["cost"], 4), "tokens": v["tokens"]} for k, v in model_usage.items()],
            key=lambda x: x["cost_usd"], reverse=True,
        )[:8]

        # ── Cost by group/LoB ──────────────────────────────────────
        group_cost = defaultdict(lambda: {"cost": 0, "calls": 0, "lob": ""})
        for r in records:
            g = group_cost[r.group_id]
            g["cost"] += r.cost_usd
            g["calls"] += 1
            if r.lob:
                g["lob"] = r.lob
        group_names = {}
        for gid in group_cost:
            grp = group_manager.get(gid) if hasattr(group_manager, "get") else None
            group_names[gid] = grp.name if grp else gid
        cost_by_group = sorted(
            [{"group_id": k, "group_name": group_names.get(k, k), "lob": v["lob"], "cost_usd": round(v["cost"], 4), "calls": v["calls"]} for k, v in group_cost.items()],
            key=lambda x: x["cost_usd"], reverse=True,
        )

        # ── Daily trend ────────────────────────────────────────────
        daily = defaultdict(lambda: {"cost": 0, "calls": 0})
        for r in records:
            day_str = r.timestamp.strftime("%Y-%m-%d") if r.timestamp else "unknown"
            daily[day_str]["cost"] += r.cost_usd
            daily[day_str]["calls"] += 1
        daily_trend = sorted([{"date": k, "cost_usd": round(v["cost"], 4), "calls": v["calls"]} for k, v in daily.items()], key=lambda x: x["date"])

        # ── Active users ───────────────────────────────────────────
        active_users = len(set(r.user_id for r in records if r.user_id))

        # ── ROI metrics ────────────────────────────────────────────
        total_agents_active = len([a for a in (agent_registry.list_all() if agent_registry else []) if getattr(a, "status", "") in ("active", "ACTIVE", "AgentStatus.ACTIVE")])
        total_workflows = len(orchestrator.list_pipelines()) if orchestrator else 0
        automated_decisions = sum(1 for r in records if r.status == "success")
        avg_time_saved_min = round(automated_decisions * 2.5, 0)  # ~2.5 min saved per automated call

        return {
            "period_days": period_days,
            "kpis": {
                "total_calls": total_calls,
                "total_cost_usd": round(total_cost, 4),
                "total_tokens": total_tokens,
                "success_rate": success_rate,
                "avg_latency_ms": avg_latency,
                "avg_cost_per_call": avg_cost_per_call,
                "cost_trend_pct": cost_trend_pct,
                "calls_trend_pct": calls_trend_pct,
                "active_users": active_users,
            },
            "top_agents": top_agents,
            "top_models": top_models,
            "cost_by_group": cost_by_group,
            "daily_trend": daily_trend,
            "roi": {
                "active_agents": total_agents_active,
                "active_workflows": total_workflows,
                "automated_decisions": automated_decisions,
                "estimated_time_saved_min": avg_time_saved_min,
                "cost_per_decision": avg_cost_per_call,
            },
        }

    @app.get("/groups", tags=["Groups"])
    async def list_groups(lob: Optional[str] = Query(default=None)):
        if lob:
            groups = group_manager.get_groups_for_lob(lob)
        else:
            groups = group_manager.list_all()
        return {
            "count": len(groups),
            "groups": [g.model_dump(mode="json") for g in groups],
        }

    @app.get("/groups/stats", tags=["Groups"])
    async def group_stats():
        return group_manager.get_stats()

    @app.get("/groups/{group_id}", tags=["Groups"])
    async def get_group(group_id: str):
        g = group_manager.get(group_id)
        if not g:
            raise HTTPException(404, f"Group '{group_id}' not found")
        return g.model_dump(mode="json")

    @app.post("/groups", tags=["Groups"])
    async def create_group(req: CreateGroupRequest):
        g = group_manager.create(
            name=req.name,
            description=req.description,
            lob=req.lob,
            allowed_model_ids=req.allowed_model_ids,
            allowed_agent_ids=req.allowed_agent_ids,
            assigned_roles=req.assigned_roles,
            monthly_budget_usd=req.monthly_budget_usd,
        )
        return {"status": "created", "group_id": g.group_id}

    @app.put("/groups/{group_id}", tags=["Groups"])
    async def update_group(group_id: str, req: UpdateGroupRequest):
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        g = group_manager.update(group_id, **updates)
        if not g:
            raise HTTPException(404, f"Group '{group_id}' not found")
        return {"status": "updated", "group_id": group_id}

    @app.delete("/groups/{group_id}", tags=["Groups"])
    async def delete_group(group_id: str):
        if not group_manager.delete(group_id):
            raise HTTPException(404, f"Group '{group_id}' not found")
        return {"status": "deleted"}

    # ── Member Management ─────────────────────────────────────────

    @app.get("/groups/{group_id}/members", tags=["Groups"])
    async def list_group_members(group_id: str):
        g = group_manager.get(group_id)
        if not g:
            raise HTTPException(404, f"Group '{group_id}' not found")
        return {"group_id": group_id, "members": g.member_ids}

    @app.post("/groups/{group_id}/members", tags=["Groups"])
    async def add_group_member(group_id: str, req: AddMemberRequest):
        if not group_manager.add_member(group_id, req.user_id):
            raise HTTPException(404, f"Group '{group_id}' not found")
        return {"status": "added", "group_id": group_id, "user_id": req.user_id}

    @app.delete("/groups/{group_id}/members/{user_id}", tags=["Groups"])
    async def remove_group_member(group_id: str, user_id: str):
        if not group_manager.remove_member(group_id, user_id):
            raise HTTPException(404, f"Group or user not found")
        return {"status": "removed", "group_id": group_id, "user_id": user_id}

    # ── Model Assignment (Admin pushes models to groups) ──────────

    @app.post("/groups/{group_id}/models", tags=["Groups"])
    async def assign_models_to_group(group_id: str, req: AssignModelsRequest):
        if not group_manager.assign_models(group_id, req.model_ids):
            raise HTTPException(404, f"Group '{group_id}' not found")
        return {"status": "assigned", "group_id": group_id, "model_ids": req.model_ids}

    @app.delete("/groups/{group_id}/models", tags=["Groups"])
    async def revoke_models_from_group(group_id: str, req: AssignModelsRequest):
        if not group_manager.revoke_models(group_id, req.model_ids):
            raise HTTPException(404, f"Group '{group_id}' not found")
        return {"status": "revoked", "group_id": group_id, "model_ids": req.model_ids}

    @app.get("/groups/{group_id}/models", tags=["Groups"])
    async def list_group_models(group_id: str):
        g = group_manager.get(group_id)
        if not g:
            raise HTTPException(404, f"Group '{group_id}' not found")
        # Optionally enrich with model details
        models = []
        if model_library:
            for mid in g.allowed_model_ids:
                m = model_library.get(mid)
                if m:
                    models.append(m.model_dump(mode="json"))
                else:
                    models.append({"model_id": mid, "display_name": mid})
        else:
            models = [{"model_id": mid} for mid in g.allowed_model_ids]
        return {"group_id": group_id, "models": models}

    # ── Agent Assignment ──────────────────────────────────────────

    @app.post("/groups/{group_id}/agents", tags=["Groups"])
    async def assign_agents_to_group(group_id: str, req: AssignAgentsRequest):
        if not group_manager.assign_agents(group_id, req.agent_ids):
            raise HTTPException(404, f"Group '{group_id}' not found")
        return {"status": "assigned", "group_id": group_id, "agent_ids": req.agent_ids}

    @app.delete("/groups/{group_id}/agents", tags=["Groups"])
    async def revoke_agents_from_group(group_id: str, req: AssignAgentsRequest):
        if not group_manager.revoke_agents(group_id, req.agent_ids):
            raise HTTPException(404, f"Group '{group_id}' not found")
        return {"status": "revoked", "group_id": group_id, "agent_ids": req.agent_ids}

    # ── Role Assignment ───────────────────────────────────────────

    @app.post("/groups/{group_id}/roles", tags=["Groups"])
    async def assign_roles_to_group(group_id: str, req: AssignRolesRequest):
        if not group_manager.assign_roles(group_id, req.roles):
            raise HTTPException(404, f"Group '{group_id}' not found")
        return {"status": "assigned", "group_id": group_id, "roles": req.roles}

    # ── User's allowed models (via group membership) ──────────────

    @app.get("/users/{user_id}/allowed-models", tags=["Groups"])
    async def get_user_allowed_models(user_id: str):
        model_ids = group_manager.get_user_allowed_models(user_id)
        return {"user_id": user_id, "allowed_model_ids": model_ids}

    @app.get("/users/{user_id}/groups", tags=["Groups"])
    async def get_user_groups(user_id: str):
        groups = group_manager.get_user_groups(user_id)
        return {"user_id": user_id, "groups": [g.model_dump(mode="json") for g in groups]}

    # ══════════════════════════════════════════════════════════════
    # USAGE METERING & COST REPORTS
    # ══════════════════════════════════════════════════════════════

    @app.get("/metering/summary", tags=["Metering"])
    async def metering_summary(
        group_id: Optional[str] = Query(default=None),
        lob: Optional[str] = Query(default=None),
        agent_id: Optional[str] = Query(default=None),
        period_days: int = Query(default=30),
    ):
        return usage_metering.summary(group_id=group_id, lob=lob, agent_id=agent_id, period_days=period_days)

    @app.get("/metering/by-group", tags=["Metering"])
    async def metering_by_group(period_days: int = Query(default=30)):
        data = usage_metering.by_group(period_days=period_days)
        return {"dimension": "group", "period_days": period_days, "data": [d.model_dump() for d in data]}

    @app.get("/metering/by-lob", tags=["Metering"])
    async def metering_by_lob(period_days: int = Query(default=30)):
        data = usage_metering.by_lob(period_days=period_days)
        return {"dimension": "lob", "period_days": period_days, "data": [d.model_dump() for d in data]}

    @app.get("/metering/by-agent", tags=["Metering"])
    async def metering_by_agent(
        group_id: Optional[str] = Query(default=None),
        lob: Optional[str] = Query(default=None),
        period_days: int = Query(default=30),
    ):
        kwargs = {}
        if group_id:
            kwargs["group_id"] = group_id
        if lob:
            kwargs["lob"] = lob
        data = usage_metering.by_agent(period_days=period_days, **kwargs)
        return {"dimension": "agent", "period_days": period_days, "data": [d.model_dump() for d in data]}

    @app.get("/metering/by-model", tags=["Metering"])
    async def metering_by_model(
        group_id: Optional[str] = Query(default=None),
        lob: Optional[str] = Query(default=None),
        period_days: int = Query(default=30),
    ):
        kwargs = {}
        if group_id:
            kwargs["group_id"] = group_id
        if lob:
            kwargs["lob"] = lob
        data = usage_metering.by_model(period_days=period_days, **kwargs)
        return {"dimension": "model", "period_days": period_days, "data": [d.model_dump() for d in data]}

    @app.get("/metering/by-user", tags=["Metering"])
    async def metering_by_user(
        group_id: Optional[str] = Query(default=None),
        period_days: int = Query(default=30),
    ):
        kwargs = {}
        if group_id:
            kwargs["group_id"] = group_id
        data = usage_metering.by_user(period_days=period_days, **kwargs)
        return {"dimension": "user", "period_days": period_days, "data": [d.model_dump() for d in data]}

    @app.get("/metering/trend", tags=["Metering"])
    async def metering_trend(
        group_id: Optional[str] = Query(default=None),
        lob: Optional[str] = Query(default=None),
        period_days: int = Query(default=30),
    ):
        return {
            "period_days": period_days,
            "trend": usage_metering.daily_trend(group_id=group_id, lob=lob, period_days=period_days),
        }

    @app.get("/metering/billing-export", tags=["Metering"])
    async def billing_export(
        group_id: Optional[str] = Query(default=None),
        lob: Optional[str] = Query(default=None),
        period_days: int = Query(default=30),
    ):
        """Generate a billing export with cost breakdowns for chargeback."""
        return usage_metering.export_billing(group_id=group_id, lob=lob, period_days=period_days)

    @app.get("/metering/pricing", tags=["Metering"])
    async def get_pricing_table():
        """Return the model pricing table used for cost calculations."""
        from backend.metering.usage_metering import MODEL_PRICING
        return {
            "models": [
                {"model_id": k, "input_cost_per_1k": v[0], "output_cost_per_1k": v[1]}
                for k, v in MODEL_PRICING.items()
            ]
        }

    # ══════════════════════════════════════════════════════════════
    # LLM INTEGRATIONS (Admin-managed provider credentials)
    # ══════════════════════════════════════════════════════════════

    if integration_manager:

        @app.get("/integrations", tags=["Integrations"])
        async def list_integrations(provider: Optional[str] = Query(default=None)):
            if provider:
                integrations = integration_manager.list_by_provider(provider)
            else:
                integrations = integration_manager.list_all()
            safe = []
            for i in integrations:
                d = i.model_dump(mode="json")
                d.pop("api_key", None)
                d.pop("service_account_json", None)
                safe.append(d)
            return {"count": len(safe), "integrations": safe}

        @app.get("/integrations/stats", tags=["Integrations"])
        async def integration_stats():
            return integration_manager.get_stats()

        @app.get("/integrations/{integration_id}", tags=["Integrations"])
        async def get_integration(integration_id: str):
            d = integration_manager.get_safe(integration_id)
            if not d:
                raise HTTPException(404, f"Integration '{integration_id}' not found")
            return d

        @app.post("/integrations", tags=["Integrations"])
        async def create_integration(req: CreateIntegrationRequest):
            i = await integration_manager.create_async(
                name=req.name,
                provider=req.provider,
                api_key=req.api_key,
                auth_type=req.auth_type,
                service_account_json=req.service_account_json,
                description=req.description,
                endpoint_url=req.endpoint_url,
                project_id=req.project_id,
                default_model=req.default_model,
                allowed_models=req.allowed_models,
                registered_models=req.registered_models,
                rate_limit_rpm=req.rate_limit_rpm,
                assigned_group_ids=req.assigned_group_ids,
            )
            # Register selected models into ModelLibrary
            if req.registered_models:
                from backend.llm_registry.model_library import ModelEntry, ModelProvider as MP
                from backend.api.server import _get_model_pricing
                prov_map = {"google": MP.GOOGLE, "openai": MP.OPENAI, "anthropic": MP.ANTHROPIC, "ollama": MP.OLLAMA}
                prov = prov_map.get(req.provider)
                if prov:
                    for m in req.registered_models:
                        if m not in model_library._models:
                            model_library.register(ModelEntry(
                                model_id=m, display_name=m, provider=prov, model_name=m,
                                description=f"From integration '{req.name}'",
                                requires_api_key=(req.auth_type == "api_key"),
                                is_local=(req.provider == "ollama"),
                                pricing=_get_model_pricing(m),
                                metadata={"integration_id": i.integration_id},
                            ))
            return {"status": "created", "integration_id": i.integration_id}

        @app.put("/integrations/{integration_id}", tags=["Integrations"])
        async def update_integration(integration_id: str, req: UpdateIntegrationRequest):
            updates = {k: v for k, v in req.model_dump().items() if v is not None}
            i = await integration_manager.update_async(integration_id, **updates)
            if not i:
                raise HTTPException(404, f"Integration '{integration_id}' not found")
            # Re-register models if registered_models changed
            if req.registered_models is not None:
                from backend.llm_registry.model_library import ModelEntry, ModelProvider as MP
                prov_map = {"google": MP.GOOGLE, "openai": MP.OPENAI, "anthropic": MP.ANTHROPIC, "ollama": MP.OLLAMA}
                intg = integration_manager.get(integration_id)
                prov = prov_map.get(intg.provider.value) if intg else None
                if prov:
                    for m in req.registered_models:
                        if m not in model_library._models:
                            model_library.register(ModelEntry(
                                model_id=m, display_name=m, provider=prov, model_name=m,
                                description=f"From integration '{intg.name}'",
                                metadata={"integration_id": integration_id},
                            ))
            return {"status": "updated", "integration_id": integration_id}

        @app.delete("/integrations/{integration_id}", tags=["Integrations"])
        async def delete_integration(integration_id: str):
            # Remove registered models from ModelLibrary
            intg = integration_manager.get(integration_id)
            if intg:
                for m in (intg.registered_models or []):
                    model_library.unregister(m)
            if not await integration_manager.delete_async(integration_id):
                raise HTTPException(404, f"Integration '{integration_id}' not found")
            return {"status": "deleted"}

        @app.post("/integrations/{integration_id}/push", tags=["Integrations"])
        async def push_integration_to_groups(integration_id: str, req: PushIntegrationRequest):
            if not await integration_manager.push_to_groups_async(integration_id, req.group_ids):
                raise HTTPException(404, f"Integration '{integration_id}' not found")
            return {"status": "pushed", "integration_id": integration_id, "group_ids": req.group_ids}

        @app.post("/integrations/{integration_id}/revoke", tags=["Integrations"])
        async def revoke_integration_from_groups(integration_id: str, req: PushIntegrationRequest):
            if not await integration_manager.revoke_from_groups_async(integration_id, req.group_ids):
                raise HTTPException(404, f"Integration '{integration_id}' not found")
            return {"status": "revoked", "integration_id": integration_id, "group_ids": req.group_ids}

        @app.get("/integrations/by-group/{group_id}", tags=["Integrations"])
        async def get_group_integrations(group_id: str):
            integrations = integration_manager.get_group_integrations(group_id)
            safe = []
            for i in integrations:
                d = i.model_dump(mode="json")
                d.pop("api_key", None)
                d.pop("service_account_json", None)
                safe.append(d)
            return {"group_id": group_id, "integrations": safe}

        @app.post("/integrations/{integration_id}/test", tags=["Integrations"])
        async def test_integration(integration_id: str):
            """Test connectivity and return available models from the provider."""
            i = integration_manager.get(integration_id)
            if not i:
                raise HTTPException(404, f"Integration '{integration_id}' not found")
            try:
                models = await _list_provider_models(i)
                await integration_manager.mark_tested_async(integration_id, True)
                return {"status": "success", "integration_id": integration_id, "models": models}
            except Exception as e:
                await integration_manager.mark_tested_async(integration_id, False, str(e))
                return {"status": "error", "integration_id": integration_id, "error": str(e), "models": []}

        @app.post("/integrations/test-connection", tags=["Integrations"])
        async def test_connection_inline(req: CreateIntegrationRequest):
            """Test connectivity with credentials before saving — returns available models."""
            from backend.integrations.llm_integration_manager import LLMIntegration, LLMProvider as LP
            tmp = LLMIntegration(
                name=req.name, provider=LP(req.provider), auth_type=req.auth_type,
                api_key=req.api_key, service_account_json=req.service_account_json or {},
                endpoint_url=req.endpoint_url, project_id=req.project_id,
            )
            try:
                models = await _list_provider_models(tmp)
                return {"status": "success", "models": models}
            except Exception as e:
                return {"status": "error", "error": str(e), "models": []}

        async def _list_provider_models(intg) -> list:
            """Call the provider's list-models API and return a list of model name strings."""
            import asyncio
            provider = intg.provider.value if hasattr(intg.provider, 'value') else intg.provider

            if provider == "google":
                return await asyncio.to_thread(_list_google_models, intg)
            elif provider == "openai":
                return await asyncio.to_thread(_list_openai_models, intg)
            elif provider == "anthropic":
                return await asyncio.to_thread(_list_anthropic_models, intg)
            elif provider == "ollama":
                return await asyncio.to_thread(_list_ollama_models, intg)
            else:
                return []

        def _list_google_models(intg) -> list:
            """List Gemini models using the google-genai SDK."""
            from google import genai as google_genai
            if intg.auth_type == "service_account" and intg.service_account_json:
                from google.oauth2 import service_account as sa
                creds = sa.Credentials.from_service_account_info(
                    intg.service_account_json,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                project = intg.service_account_json.get("project_id") or intg.project_id or ""
                client = google_genai.Client(
                    vertexai=True,
                    credentials=creds,
                    project=project,
                    location=intg.endpoint_url or "us-central1",
                )
            else:
                client = google_genai.Client(api_key=intg.api_key)
            models = []
            for m in client.models.list():
                raw = m.name if hasattr(m, "name") else str(m)
                # Normalise: strip common prefixes to get bare model id
                clean = raw
                for prefix in ("publishers/google/models/", "models/"):
                    if clean.startswith(prefix):
                        clean = clean[len(prefix):]
                        break
                if clean.startswith("gemini"):
                    if clean not in models:
                        models.append(clean)
            return sorted(models)

        def _list_openai_models(intg) -> list:
            """List models from OpenAI API."""
            import httpx
            base = intg.endpoint_url or "https://api.openai.com/v1"
            resp = httpx.get(f"{base}/models", headers={"Authorization": f"Bearer {intg.api_key}"}, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return sorted([m["id"] for m in data if "gpt" in m["id"] or m["id"].startswith("o")])

        def _list_anthropic_models(intg) -> list:
            """List models from Anthropic API."""
            import httpx
            resp = httpx.get("https://api.anthropic.com/v1/models",
                             headers={"x-api-key": intg.api_key, "anthropic-version": "2023-06-01"}, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return sorted([m["id"] for m in data])

        def _list_ollama_models(intg) -> list:
            """List models from local Ollama instance."""
            import httpx
            base = intg.endpoint_url or "http://localhost:11434"
            resp = httpx.get(f"{base}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json().get("models", [])
            return sorted([m["name"] for m in data])

    # ══════════════════════════════════════════════════════════════
    # AGENT-AS-A-SERVICE: Invoke Agent & Workflow via API
    # ══════════════════════════════════════════════════════════════

    import time as _time
    import uuid as _uuid
    import hashlib as _hl

    # ── Token auth helper ──────────────────────────────────────────
    def _verify_token(authorization: Optional[str]) -> bool:
        """Verify Bearer token against api_token_store. Returns True if valid."""
        if not api_token_store:
            return True  # no tokens configured = open access (dev mode)
        if not authorization or not authorization.startswith("Bearer jai-tk-"):
            return False
        raw = authorization.replace("Bearer ", "")
        h = _hl.sha256(raw.encode()).hexdigest()
        for t in api_token_store:
            if t.get("token_hash") == h and t.get("status") == "active":
                t["last_used"] = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
                return True
        return False

    # ══════════════════════════════════════════════════════════════
    # API TOKEN MANAGEMENT
    # ══════════════════════════════════════════════════════════════

    @app.get("/api-tokens", tags=["Auth"])
    async def list_api_tokens():
        tokens = api_token_store or []
        safe = [{"token_id": t["token_id"], "name": t["name"], "token_prefix": t["token_prefix"],
                 "created_at": t["created_at"], "last_used": t.get("last_used"), "status": t["status"]} for t in tokens]
        return {"count": len(safe), "tokens": safe}

    @app.post("/api-tokens", tags=["Auth"])
    async def create_api_token(req: CreateTokenRequest):
        token_raw = f"jai-tk-{_uuid.uuid4().hex[:24]}"
        token_obj = {
            "token_id": f"tok-{_uuid.uuid4().hex[:8]}",
            "name": req.name,
            "token_prefix": token_raw[:12] + "...",
            "token_hash": _hl.sha256(token_raw.encode()).hexdigest(),
            "token_plain": token_raw,
            "created_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
            "last_used": None,
            "status": "active",
        }
        if api_token_store is not None:
            api_token_store.append(token_obj)
        # Return the plain token ONCE — user must copy it now
        return {"token_id": token_obj["token_id"], "name": req.name, "token": token_raw, "message": "Copy this token now — it will not be shown again."}

    @app.delete("/api-tokens/{token_id}", tags=["Auth"])
    async def revoke_api_token(token_id: str):
        if api_token_store:
            for t in api_token_store:
                if t["token_id"] == token_id:
                    t["status"] = "revoked"
                    return {"status": "revoked", "token_id": token_id}
        raise HTTPException(404, "Token not found")

    @app.post("/agents/{agent_id}/invoke", tags=["Agents"])
    async def invoke_agent(agent_id: str, req: InvokeAgentRequest, authorization: Optional[str] = Header(default=None)):
        """
        Invoke an agent with a message. Returns structured response.
        This is the primary AaaS endpoint for programmatic agent usage.
        """
        if not _verify_token(authorization):
            raise HTTPException(401, "Invalid or missing API token. Create one at Settings → API Tokens.")
        if not agent_registry:
            raise HTTPException(501, "Agent registry not available")
        agent = agent_registry.get(agent_id)
        if not agent:
            raise HTTPException(404, f"Agent '{agent_id}' not found")

        start = _time.time()
        run_id = f"run-{_uuid.uuid4().hex[:8]}"

        # Build the model to use (agent default or override)
        model = req.model or (agent.model_config_.model_id if hasattr(agent, "model_config_") else "gemini-2.5-flash")

        # Attempt real completion via gateway if available
        if gateway:
            from backend.gateway.aaas_gateway import GatewayRequest
            messages = []
            # Add system prompt from agent config
            sys_prompt = getattr(agent, "context", {})
            if isinstance(sys_prompt, dict) and sys_prompt.get("system_prompt"):
                messages.append({"role": "system", "content": sys_prompt["system_prompt"]})
            elif hasattr(agent, "system_prompt") and agent.system_prompt:
                messages.append({"role": "system", "content": agent.system_prompt})
            # Add context as system message
            if req.context:
                messages.append({"role": "system", "content": f"Context: {str(req.context)}"})
            messages.append({"role": "user", "content": req.message})

            gw_req = GatewayRequest(
                model=model,
                messages=messages,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                agent_id=agent_id,
            )
            try:
                resp = await gateway.process_completion(gw_req, "tenant-default")
                latency_ms = round((_time.time() - start) * 1000, 1)
                output = resp.choices[0].message.get("content", "") if resp.choices else ""
                # Log
                if llm_log_manager:
                    llm_log_manager.log_request(
                        tenant_id="tenant-default", agent_id=agent_id,
                        model=resp.model, provider=resp.model.split("-")[0] if "-" in resp.model else "unknown",
                        prompt=req.message[:200], response=output[:200],
                        prompt_tokens=resp.usage.prompt_tokens,
                        completion_tokens=resp.usage.completion_tokens,
                        latency_ms=latency_ms, cost_usd=resp.cost_usd,
                    )
                return {
                    "run_id": run_id,
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "model": resp.model,
                    "output": output,
                    "usage": {"prompt_tokens": resp.usage.prompt_tokens, "completion_tokens": resp.usage.completion_tokens, "total_tokens": resp.usage.total_tokens},
                    "cost_usd": resp.cost_usd,
                    "latency_ms": latency_ms,
                    "status": "success",
                }
            except Exception as e:
                latency_ms = round((_time.time() - start) * 1000, 1)
                return {
                    "run_id": run_id, "agent_id": agent_id, "agent_name": agent.name,
                    "model": model, "output": "", "error": str(e),
                    "latency_ms": latency_ms, "status": "error",
                }
        else:
            # Simulated response when no gateway
            latency_ms = round((_time.time() - start) * 1000, 1) + 150
            return {
                "run_id": run_id,
                "agent_id": agent_id,
                "agent_name": agent.name,
                "model": model,
                "output": f"[Simulated] Agent '{agent.name}' processed: {req.message[:100]}",
                "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
                "cost_usd": 0.0003,
                "latency_ms": latency_ms,
                "status": "success",
            }

    @app.post("/workflows/{pipeline_id}/invoke", tags=["Pipelines"])
    async def invoke_workflow(pipeline_id: str, req: InvokeWorkflowRequest, authorization: Optional[str] = Header(default=None)):
        """
        Invoke a workflow (pipeline) with input data. Returns structured response.
        This is the primary AaaS endpoint for programmatic workflow usage.
        """
        if not _verify_token(authorization):
            raise HTTPException(401, "Invalid or missing API token. Create one at Settings → API Tokens.")
        if not orchestrator:
            raise HTTPException(501, "Orchestrator not available")
        pipe = orchestrator.get_pipeline(pipeline_id)
        if not pipe:
            raise HTTPException(404, f"Workflow '{pipeline_id}' not found")

        input_data = req.input_data or {}
        if req.message:
            input_data["message"] = req.message

        run = orchestrator.execute_pipeline(pipeline_id, input_data)
        return {
            "run_id": run.run_id,
            "workflow_id": pipeline_id,
            "workflow_name": pipe.name,
            "status": run.status,
            "steps_completed": run.steps_completed,
            "steps_total": run.steps_total,
            "output": run.output_data,
            "step_results": run.step_results,
            "total_latency_ms": run.total_latency_ms,
            "total_cost_usd": run.total_cost,
        }

    @app.get("/agents/{agent_id}/api-snippet", tags=["Agents"])
    async def agent_api_snippet(agent_id: str):
        """Return ready-to-use curl and Python code for invoking this agent."""
        if not agent_registry:
            raise HTTPException(501, "Agent registry not available")
        agent = agent_registry.get(agent_id)
        if not agent:
            raise HTTPException(404, f"Agent '{agent_id}' not found")

        base_url = "http://localhost:8080"
        curl = f'''curl -X POST {base_url}/agents/{agent_id}/invoke \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_TOKEN" \\
  -d '{{
    "message": "Hello, what can you help me with?",
    "context": {{}},
    "temperature": 0.7,
    "max_tokens": 4096
  }}'
'''
        python = f'''import requests

API_TOKEN = "YOUR_API_TOKEN"  # Create at Settings → API Tokens

response = requests.post(
    "{base_url}/agents/{agent_id}/invoke",
    headers={{"Authorization": f"Bearer {{API_TOKEN}}"}},
    json={{
        "message": "Hello, what can you help me with?",
        "context": {{}},
        "temperature": 0.7,
        "max_tokens": 4096,
    }},
)
result = response.json()
print(result["output"])
# => Agent response text
# result["usage"]       — token counts
# result["cost_usd"]    — cost in USD
# result["latency_ms"]  — response time
'''
        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "endpoint": f"POST /agents/{agent_id}/invoke",
            "curl": curl,
            "python": python,
        }

    @app.get("/workflows/{pipeline_id}/api-snippet", tags=["Pipelines"])
    async def workflow_api_snippet(pipeline_id: str):
        """Return ready-to-use curl and Python code for invoking this workflow."""
        if not orchestrator:
            raise HTTPException(501, "Orchestrator not available")
        pipe = orchestrator.get_pipeline(pipeline_id)
        if not pipe:
            raise HTTPException(404, f"Workflow '{pipeline_id}' not found")

        base_url = "http://localhost:8080"
        curl = f'''curl -X POST {base_url}/workflows/{pipeline_id}/invoke \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_TOKEN" \\
  -d '{{
    "message": "Process this request",
    "input_data": {{
      "query": "your input here"
    }}
  }}'
'''
        python = f'''import requests

API_TOKEN = "YOUR_API_TOKEN"  # Create at Settings → API Tokens

response = requests.post(
    "{base_url}/workflows/{pipeline_id}/invoke",
    headers={{"Authorization": f"Bearer {{API_TOKEN}}"}},
    json={{
        "message": "Process this request",
        "input_data": {{
            "query": "your input here",
        }},
    }},
)
result = response.json()
print(result["output"])
# => Workflow output data
# result["status"]            — success/failed
# result["steps_completed"]   — steps executed
# result["step_results"]      — per-step outputs
# result["total_latency_ms"]  — total execution time
'''
        return {
            "workflow_id": pipeline_id,
            "workflow_name": pipe.name,
            "endpoint": f"POST /workflows/{pipeline_id}/invoke",
            "curl": curl,
            "python": python,
        }
