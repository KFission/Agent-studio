"""
Tests for EnvironmentManager — environments, variables, promotions, diffs.
Run: pytest tests/test_environment_manager.py -v
"""
import pytest
from backend.environments.environment_manager import EnvironmentManager


class TestEnvironmentCRUD:

    def test_default_environments_exist(self, environment_manager):
        envs = environment_manager.get_environments("tenant-default")
        env_ids = [e.env_id for e in envs]
        assert "dev" in env_ids
        assert "qa" in env_ids
        assert "uat" in env_ids
        assert "prod" in env_ids

    def test_get_environment(self, environment_manager):
        env = environment_manager.get_environment("dev", "tenant-default")
        assert env is not None
        assert env.env_id == "dev"
        assert env.label == "DEV"

    def test_get_nonexistent_environment(self, environment_manager):
        assert environment_manager.get_environment("staging", "tenant-default") is None


class TestEnvironmentVariables:

    def test_set_variable(self, environment_manager):
        var = environment_manager.set_variable(
            "dev", "API_KEY", "test-123", is_secret=True,
            description="Test key", updated_by="admin", tenant_id="tenant-default",
        )
        assert var is not None
        assert var.key == "API_KEY"
        assert var.is_secret is True
        assert var.value == "test-123"

    def test_get_variables(self, environment_manager):
        environment_manager.set_variable("dev", "VAR_A", "val_a", tenant_id="tenant-default")
        environment_manager.set_variable("dev", "VAR_B", "val_b", tenant_id="tenant-default")
        variables = environment_manager.get_variables("dev", "tenant-default")
        assert "VAR_A" in variables
        assert "VAR_B" in variables

    def test_secret_masking(self, environment_manager):
        environment_manager.set_variable(
            "dev", "SECRET", "super-secret", is_secret=True, tenant_id="tenant-default",
        )
        variables = environment_manager.get_variables("dev", "tenant-default", include_secrets=False)
        assert variables["SECRET"]["value"] != "super-secret"
        assert "•" in variables["SECRET"]["value"]

    def test_secret_reveal(self, environment_manager):
        environment_manager.set_variable(
            "dev", "SECRET2", "reveal-me", is_secret=True, tenant_id="tenant-default",
        )
        variables = environment_manager.get_variables("dev", "tenant-default", include_secrets=True)
        assert variables["SECRET2"]["value"] == "reveal-me"

    def test_delete_variable(self, environment_manager):
        environment_manager.set_variable("dev", "TO_DEL", "val", tenant_id="tenant-default")
        assert environment_manager.delete_variable("dev", "TO_DEL", "tenant-default") is True
        variables = environment_manager.get_variables("dev", "tenant-default")
        assert "TO_DEL" not in variables

    def test_delete_nonexistent_variable(self, environment_manager):
        assert environment_manager.delete_variable("dev", "NOPE", "tenant-default") is False

    def test_bulk_set_variables(self, environment_manager):
        count = environment_manager.bulk_set_variables(
            "dev", {"BULK_1": "a", "BULK_2": "b"}, "admin", "tenant-default",
        )
        assert count == 2

    def test_cannot_set_on_locked_env(self, environment_manager):
        environment_manager.lock_environment("dev", "admin", "tenant-default")
        result = environment_manager.set_variable("dev", "BLOCKED", "val", tenant_id="tenant-default")
        assert result is None
        environment_manager.unlock_environment("dev", "tenant-default")


class TestEnvironmentLocking:

    def test_lock_environment(self, environment_manager):
        assert environment_manager.lock_environment("qa", "admin", "tenant-default") is True
        env = environment_manager.get_environment("qa", "tenant-default")
        assert env.is_locked is True
        assert env.locked_by == "admin"

    def test_unlock_environment(self, environment_manager):
        environment_manager.lock_environment("qa", "admin", "tenant-default")
        assert environment_manager.unlock_environment("qa", "tenant-default") is True
        env = environment_manager.get_environment("qa", "tenant-default")
        assert env.is_locked is False

    def test_lock_nonexistent(self, environment_manager):
        assert environment_manager.lock_environment("staging", "admin", "tenant-default") is False


class TestPromotions:

    def test_request_promotion_dev_to_qa_auto_approves(self, environment_manager):
        promo = environment_manager.request_promotion(
            asset_type="agent", asset_id="agt-001", asset_name="Test Agent",
            from_env="dev", to_env="qa", config_json={"model": "gemini"},
            requested_by="admin", tenant_id="tenant-default",
        )
        assert promo.promotion_id.startswith("promo-")
        assert promo.asset_type == "agent"
        assert promo.from_env == "dev"
        assert promo.to_env == "qa"
        # dev→qa is auto-approved and deployed
        assert promo.status.value in ("approved", "deployed")

    def test_invalid_promotion_order(self, environment_manager):
        with pytest.raises(ValueError, match="Cannot promote"):
            environment_manager.request_promotion(
                asset_type="agent", asset_id="agt-bad", asset_name="Bad",
                from_env="prod", to_env="dev", config_json={},
                requested_by="admin", tenant_id="tenant-default",
            )

    def test_approve_promotion(self, environment_manager):
        # qa→uat requires approval (not auto-approved)
        promo = environment_manager.request_promotion(
            asset_type="agent", asset_id="agt-approve", asset_name="Approve Me",
            from_env="qa", to_env="uat", config_json={"model": "gemini"},
            requested_by="admin", tenant_id="tenant-default",
        )
        assert promo.status.value == "pending"
        approved = environment_manager.approve_promotion(promo.promotion_id, "reviewer")
        assert approved is not None
        assert approved.status.value in ("approved", "deployed")

    def test_reject_promotion(self, environment_manager):
        promo = environment_manager.request_promotion(
            asset_type="agent", asset_id="agt-reject", asset_name="Reject Me",
            from_env="qa", to_env="uat", config_json={"model": "gemini"},
            requested_by="admin", tenant_id="tenant-default",
        )
        rejected = environment_manager.reject_promotion(promo.promotion_id, "reviewer", "Not ready")
        assert rejected is not None
        assert rejected.status.value == "rejected"

    def test_list_promotions(self, environment_manager):
        environment_manager.request_promotion(
            asset_type="agent", asset_id="agt-list", asset_name="List Agent",
            from_env="dev", to_env="qa", config_json={"model": "gemini"},
            requested_by="admin", tenant_id="tenant-default",
        )
        promos = environment_manager.list_promotions("tenant-default")
        assert len(promos) >= 1

    def test_get_promotion(self, environment_manager):
        promo = environment_manager.request_promotion(
            asset_type="tool", asset_id="tool-001", asset_name="Test Tool",
            from_env="dev", to_env="qa", config_json={"code": "print()"},
            requested_by="admin", tenant_id="tenant-default",
        )
        fetched = environment_manager.get_promotion(promo.promotion_id)
        assert fetched is not None
        assert fetched.asset_id == "tool-001"

    def test_rollback_promotion(self, environment_manager):
        # dev→qa auto-deploys, so we can rollback
        promo = environment_manager.request_promotion(
            asset_type="agent", asset_id="agt-rollback", asset_name="Rollback Agent",
            from_env="dev", to_env="qa", config_json={"model": "gemini"},
            requested_by="admin", tenant_id="tenant-default",
        )
        assert promo.status.value == "deployed"
        rolled = environment_manager.rollback_promotion(promo.promotion_id, "admin")
        assert rolled is not None
        assert rolled.status.value == "rolled_back"


class TestEnvironmentDiff:

    def test_diff_environments(self, environment_manager):
        environment_manager.request_promotion(
            asset_type="agent", asset_id="agt-diff", asset_name="Diff Agent",
            from_env="dev", to_env="qa", config_json={"model": "gemini"},
            requested_by="admin", tenant_id="tenant-default",
        )
        diff = environment_manager.diff_environments("dev", "qa", tenant_id="tenant-default")
        assert isinstance(diff, dict)
        assert "env_a" in diff
        assert "env_b" in diff

    def test_environment_stats(self, environment_manager):
        stats = environment_manager.get_stats("tenant-default")
        assert "environments" in stats
        assert stats["environments"] == 4
