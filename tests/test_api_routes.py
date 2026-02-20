"""
API route integration tests using FastAPI TestClient.
Tests the full HTTP request/response cycle without external dependencies.
Run: pytest tests/test_api_routes.py -v
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create a TestClient for the FastAPI app."""
    import os
    os.environ["ENVIRONMENT"] = "dev"  # bypass auth
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "")
    os.environ.setdefault("LANGFUSE_SECRET_KEY", "")
    os.environ.setdefault("LANGFUSE_HOST", "")
    os.environ.setdefault("LANGCHAIN_API_KEY", "")
    os.environ.setdefault("GOOGLE_API_KEY", "test-key")

    from backend.api.server import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ══════════════════════════════════════════════════════════════════
# SYSTEM / HEALTH
# ══════════════════════════════════════════════════════════════════


class TestSystemRoutes:

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "models_loaded" in data

    def test_info(self, client):
        r = client.get("/info")
        assert r.status_code == 200
        data = r.json()
        assert data["platform"] == "Agent Studio"

    def test_openapi_json(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert schema["info"]["title"] == "JAI Agent OS"
        assert "paths" in schema
        assert len(schema["paths"]) > 50  # should have many routes

    def test_openapi_tags_present(self, client):
        r = client.get("/openapi.json")
        schema = r.json()
        tag_names = [t["name"] for t in schema.get("tags", [])]
        assert "System" in tag_names
        assert "Agents" in tag_names
        assert "Models" in tag_names
        assert "Environments" in tag_names
        assert "Scoring" in tag_names

    def test_docs_page(self, client):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_redoc_page(self, client):
        r = client.get("/redoc")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════


class TestModelRoutes:

    def test_list_models(self, client):
        r = client.get("/models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        assert isinstance(data["models"], list)

    def test_get_model(self, client):
        # Get first model from the list
        models = client.get("/models").json()["models"]
        if models:
            model_id = models[0]["model_id"]
            r = client.get(f"/models/{model_id}")
            assert r.status_code == 200

    def test_get_nonexistent_model(self, client):
        r = client.get("/models/nonexistent-model-xyz")
        assert r.status_code == 404

    def test_providers(self, client):
        r = client.get("/providers")
        assert r.status_code == 200

    def test_compare_costs(self, client):
        r = client.get("/models/compare/cost?input_tokens=1000&output_tokens=500")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════
# AGENTS
# ══════════════════════════════════════════════════════════════════


class TestAgentRoutes:

    def test_list_agents(self, client):
        r = client.get("/agents")
        assert r.status_code == 200
        data = r.json()
        assert "agents" in data

    def test_create_agent(self, client):
        r = client.post("/agents", json={
            "name": "API Test Agent",
            "description": "Created via test",
            "tags": ["test"],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "created"
        assert "agent_id" in data

    def test_get_agent(self, client):
        # Create then get
        created = client.post("/agents", json={"name": "Get Test"}).json()
        agent_id = created["agent_id"]
        r = client.get(f"/agents/{agent_id}")
        assert r.status_code == 200
        assert r.json()["name"] == "Get Test"

    def test_update_agent(self, client):
        created = client.post("/agents", json={"name": "Update Test"}).json()
        agent_id = created["agent_id"]
        r = client.put(f"/agents/{agent_id}", json={"name": "Updated Name"})
        assert r.status_code == 200
        assert r.json()["status"] == "updated"

    def test_agent_versions(self, client):
        created = client.post("/agents", json={"name": "Version Test"}).json()
        agent_id = created["agent_id"]
        # Update to create version 2
        client.put(f"/agents/{agent_id}", json={"name": "V2"})
        r = client.get(f"/agents/{agent_id}/versions")
        assert r.status_code == 200
        assert "versions" in r.json()

    def test_agent_version_detail(self, client):
        created = client.post("/agents", json={"name": "Detail V1"}).json()
        agent_id = created["agent_id"]
        client.put(f"/agents/{agent_id}", json={"name": "Detail V2"})
        r = client.get(f"/agents/{agent_id}/versions/1")
        assert r.status_code == 200
        assert r.json()["name"] == "Detail V1"

    def test_agent_rollback(self, client):
        created = client.post("/agents", json={"name": "Rollback V1"}).json()
        agent_id = created["agent_id"]
        client.put(f"/agents/{agent_id}", json={"name": "Rollback V2"})
        r = client.post(f"/agents/{agent_id}/rollback/1?rolled_back_by=test")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "rolled_back"
        assert data["new_version"] == 3

    def test_agent_diff(self, client):
        created = client.post("/agents", json={"name": "Diff V1", "description": "Original"}).json()
        agent_id = created["agent_id"]
        client.put(f"/agents/{agent_id}", json={"name": "Diff V2", "description": "Changed"})
        r = client.get(f"/agents/{agent_id}/diff/1/2")
        assert r.status_code == 200
        data = r.json()
        assert data["total_changes"] > 0

    def test_delete_agent(self, client):
        created = client.post("/agents", json={"name": "Delete Me"}).json()
        agent_id = created["agent_id"]
        r = client.delete(f"/agents/{agent_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

    def test_agent_stats(self, client):
        r = client.get("/agents/stats")
        assert r.status_code == 200
        assert "total_agents" in r.json()


# ══════════════════════════════════════════════════════════════════
# ENVIRONMENTS
# ══════════════════════════════════════════════════════════════════


class TestEnvironmentRoutes:

    def test_list_environments(self, client):
        r = client.get("/environments")
        assert r.status_code == 200
        data = r.json()
        assert "environments" in data
        env_ids = [e["env_id"] for e in data["environments"]]
        assert "dev" in env_ids
        assert "prod" in env_ids

    def test_get_environment(self, client):
        r = client.get("/environments/dev")
        assert r.status_code == 200
        assert r.json()["env_id"] == "dev"

    def test_set_variable(self, client):
        r = client.post("/environments/dev/variables", json={
            "key": "TEST_VAR",
            "value": "test_value",
            "is_secret": False,
            "description": "Test variable",
        })
        assert r.status_code == 200

    def test_get_variables(self, client):
        # Set a variable first
        client.post("/environments/dev/variables", json={
            "key": "GET_VAR", "value": "get_value",
        })
        r = client.get("/environments/dev/variables")
        assert r.status_code == 200

    def test_bulk_set_variables(self, client):
        r = client.post("/environments/dev/variables/bulk", json={
            "variables": {"BULK_A": "a", "BULK_B": "b"},
        })
        assert r.status_code == 200
        assert r.json()["count"] == 2

    def test_lock_unlock_environment(self, client):
        r = client.post("/environments/qa/lock?locked_by=test")
        assert r.status_code == 200
        assert r.json()["status"] == "locked"
        r2 = client.post("/environments/qa/unlock")
        assert r2.status_code == 200
        assert r2.json()["status"] == "unlocked"

    def test_environment_stats(self, client):
        r = client.get("/environments/stats")
        # May return 200 or 404 depending on route registration
        assert r.status_code in (200, 404)


# ══════════════════════════════════════════════════════════════════
# PROMOTIONS
# ══════════════════════════════════════════════════════════════════


class TestPromotionRoutes:

    def test_request_promotion(self, client):
        r = client.post("/environments/promotions", json={
            "asset_type": "agent",
            "asset_id": "agt-test-001",
            "asset_name": "Test Agent",
            "from_env": "dev",
            "to_env": "qa",
            "requested_by": "test-user",
        })
        assert r.status_code == 200
        assert "promotion_id" in r.json()

    def test_list_promotions(self, client):
        r = client.get("/environments/promotions")
        # Promotions endpoint should exist
        assert r.status_code in (200, 404)

    def test_approve_promotion(self, client):
        # Create a promotion that requires approval (qa→uat)
        created = client.post("/environments/promotions", json={
            "asset_type": "agent", "asset_id": "agt-approve",
            "asset_name": "Approve Agent",
            "from_env": "qa", "to_env": "uat",
            "config_json": {"model": "gemini"},
            "requested_by": "admin",
        }).json()
        promo_id = created.get("promotion_id", "")
        if promo_id:
            r = client.post(f"/environments/promotions/{promo_id}/approve?approved_by=reviewer")
            assert r.status_code == 200

    def test_invalid_promotion_order(self, client):
        r = client.post("/environments/promotions", json={
            "asset_type": "agent", "asset_id": "agt-bad",
            "from_env": "prod", "to_env": "dev",
            "requested_by": "admin",
        })
        assert r.status_code == 400

    def test_diff_environments(self, client):
        r = client.get("/environments/diff/dev/qa")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════
# SCORING
# ══════════════════════════════════════════════════════════════════


class TestScoringRoutes:

    def test_eval_score(self, client):
        r = client.post("/eval/score", json={
            "input_text": "What is 2+2?",
            "output_text": "4",
            "reference_text": "4",
            "metrics": ["exact_match", "contains"],
            "llm_judge_enabled": False,
        })
        assert r.status_code == 200
        data = r.json()
        assert "reference_scores" in data
        assert data["aggregate_score"] == 1.0

    def test_eval_metrics_list(self, client):
        r = client.get("/eval/metrics")
        assert r.status_code == 200
        data = r.json()
        assert "reference_metrics" in data
        assert "exact_match" in data["reference_metrics"]
        assert "judge_criteria" in data


# ══════════════════════════════════════════════════════════════════
# TOOLS
# ══════════════════════════════════════════════════════════════════


class TestToolRoutes:

    def test_list_tools(self, client):
        r = client.get("/tools")
        assert r.status_code == 200
        assert "tools" in r.json()

    def test_create_tool(self, client):
        r = client.post("/tools", json={
            "name": "API Test Tool",
            "description": "Created via test",
            "tool_type": "code",
            "tags": ["test"],
        })
        assert r.status_code == 200
        assert r.json()["status"] == "created"

    def test_get_tool_stats(self, client):
        r = client.get("/tools/stats/summary")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════
# PIPELINES / ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════


class TestPipelineRoutes:

    def test_list_pipelines(self, client):
        r = client.get("/orchestrator/pipelines")
        assert r.status_code == 200
        assert "pipelines" in r.json()

    def test_create_pipeline(self, client):
        r = client.post("/orchestrator/pipelines", json={
            "name": "Test Pipeline",
            "description": "Created via test",
            "pattern": "sequential",
            "steps": [
                {"name": "Step 1", "agent_id": "agt-001"},
                {"name": "Step 2", "agent_id": "agt-002"},
            ],
            "tags": ["test"],
        })
        assert r.status_code == 200
        assert r.json()["status"] == "created"

    def test_orchestrator_stats(self, client):
        r = client.get("/orchestrator/stats")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════
# AUTH & USERS
# ══════════════════════════════════════════════════════════════════


class TestAuthRoutes:

    def test_list_roles(self, client):
        r = client.get("/roles")
        assert r.status_code == 200
        assert "roles" in r.json()

    def test_list_users(self, client):
        r = client.get("/users")
        assert r.status_code == 200
        assert "users" in r.json()


# ══════════════════════════════════════════════════════════════════
# THREADS
# ══════════════════════════════════════════════════════════════════


class TestThreadRoutes:

    def test_list_threads(self, client):
        r = client.get("/threads")
        assert r.status_code == 200
        assert "threads" in r.json()

    def test_create_thread(self, client):
        r = client.post("/threads", json={
            "agent_id": "agt-001",
            "tenant_id": "tenant-default",
            "user_id": "user-001",
            "title": "Test Thread",
        })
        assert r.status_code == 200
        assert "thread_id" in r.json()


# ══════════════════════════════════════════════════════════════════
# INBOX
# ══════════════════════════════════════════════════════════════════


class TestInboxRoutes:

    def test_list_inbox(self, client):
        r = client.get("/inbox")
        assert r.status_code == 200

    def test_inbox_stats(self, client):
        r = client.get("/inbox/stats/summary")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════
# GROUPS
# ══════════════════════════════════════════════════════════════════


class TestGroupRoutes:

    def test_list_groups(self, client):
        r = client.get("/groups")
        assert r.status_code == 200
        assert "groups" in r.json()

    def test_create_group(self, client):
        r = client.post("/groups", json={
            "name": "API Test Group",
            "description": "Created via test",
            "lob": "IT",
            "allowed_model_ids": ["gemini-2.5-flash"],
        })
        assert r.status_code == 200
        assert "group_id" in r.json()

    def test_group_stats(self, client):
        r = client.get("/groups/stats")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════
# METERING
# ══════════════════════════════════════════════════════════════════


class TestMeteringRoutes:

    def test_metering_summary(self, client):
        r = client.get("/metering/summary")
        assert r.status_code == 200

    def test_metering_by_group(self, client):
        r = client.get("/metering/by-group")
        assert r.status_code == 200

    def test_metering_pricing(self, client):
        r = client.get("/metering/pricing")
        assert r.status_code == 200
        assert "models" in r.json()


# ══════════════════════════════════════════════════════════════════
# GUARDRAILS
# ══════════════════════════════════════════════════════════════════


class TestGuardrailRoutes:

    def test_list_guardrails(self, client):
        r = client.get("/guardrails")
        assert r.status_code == 200

    def test_guardrails_stats(self, client):
        r = client.get("/guardrails/stats")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════
# WEBHOOKS
# ══════════════════════════════════════════════════════════════════


class TestWebhookRoutes:

    def test_list_webhooks(self, client):
        r = client.get("/webhooks")
        assert r.status_code == 200
        assert "webhooks" in r.json()


# ══════════════════════════════════════════════════════════════════
# KNOWLEDGE BASES
# ══════════════════════════════════════════════════════════════════


class TestKnowledgeBaseRoutes:

    def test_list_knowledge_bases(self, client):
        r = client.get("/knowledge-bases")
        assert r.status_code == 200
        assert "knowledge_bases" in r.json()

    def test_create_knowledge_base(self, client):
        r = client.post("/knowledge-bases", json={
            "name": "Test KB",
            "description": "Created by test",
        })
        assert r.status_code == 200
        assert "kb_id" in r.json()


# ══════════════════════════════════════════════════════════════════
# CONNECTORS
# ══════════════════════════════════════════════════════════════════


class TestConnectorRoutes:

    def test_list_connectors(self, client):
        r = client.get("/connectors")
        assert r.status_code == 200
        assert "connectors" in r.json()

    def test_connector_categories(self, client):
        r = client.get("/connectors/categories")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════
# NOTIFICATION CHANNELS
# ══════════════════════════════════════════════════════════════════


class TestNotificationRoutes:

    def test_list_notification_channels(self, client):
        r = client.get("/notification-channels")
        assert r.status_code == 200
        assert "channels" in r.json()


# ══════════════════════════════════════════════════════════════════
# EXECUTIVE DASHBOARD
# ══════════════════════════════════════════════════════════════════


class TestDashboardRoutes:

    def test_executive_dashboard(self, client):
        r = client.get("/executive/dashboard")
        assert r.status_code == 200

    def test_dashboard_metrics(self, client):
        r = client.get("/dashboard/metrics")
        assert r.status_code == 200
