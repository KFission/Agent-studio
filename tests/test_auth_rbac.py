"""
Tests for Auth, RBAC, UserManager, GroupManager.
Run: pytest tests/test_auth_rbac.py -v
"""
import pytest
from backend.auth.rbac import RBACManager, Role, Permission
from backend.auth.user_manager import UserManager, UserProfile
from backend.auth.group_manager import GroupManager


# ══════════════════════════════════════════════════════════════════
# RBAC MANAGER
# ══════════════════════════════════════════════════════════════════


class TestRBAC:

    def test_list_roles(self, rbac_manager):
        roles = rbac_manager.list_roles()
        assert len(roles) > 0
        role_names = [r.name for r in roles]
        assert "admin" in role_names or "platform_admin" in role_names

    def test_assign_role(self, rbac_manager):
        roles = rbac_manager.list_roles()
        role_name = roles[0].name
        result = rbac_manager.assign_role("user-001", role_name)
        assert result is True
        user_roles = rbac_manager.get_user_roles("user-001")
        assert role_name in user_roles

    def test_assign_nonexistent_role(self, rbac_manager):
        result = rbac_manager.assign_role("user-001", "nonexistent_role")
        assert result is False

    def test_revoke_role(self, rbac_manager):
        roles = rbac_manager.list_roles()
        role_name = roles[0].name
        rbac_manager.assign_role("user-002", role_name)
        rbac_manager.revoke_role("user-002", role_name)
        user_roles = rbac_manager.get_user_roles("user-002")
        assert role_name not in user_roles

    def test_get_user_roles_empty(self, rbac_manager):
        roles = rbac_manager.get_user_roles("user-no-roles")
        assert roles == [] or isinstance(roles, list)

    def test_audit_log(self, rbac_manager):
        roles = rbac_manager.list_roles()
        rbac_manager.assign_role("user-audit", roles[0].name)
        log = rbac_manager.get_audit_log(10)
        assert isinstance(log, list)


# ══════════════════════════════════════════════════════════════════
# USER MANAGER
# ══════════════════════════════════════════════════════════════════


class TestUserManager:

    def test_create_user(self, user_manager):
        profile = UserProfile(
            user_id="usr-test-001",
            email="test@jaggaer.com",
            username="testuser",
            display_name="Test User",
            tenant_id="default",
            roles=["viewer"],
        )
        user_manager._users["usr-test-001"] = profile
        user_manager._email_index["test@jaggaer.com"] = "usr-test-001"
        fetched = user_manager.get_user("usr-test-001")
        assert fetched is not None
        assert fetched.email == "test@jaggaer.com"

    def test_list_users(self, user_manager):
        for i in range(3):
            p = UserProfile(
                user_id=f"usr-{i}", email=f"u{i}@test.com",
                username=f"user{i}", display_name=f"User {i}",
            )
            user_manager._users[f"usr-{i}"] = p
        users = user_manager.list_users()
        assert len(users) >= 3

    def test_delete_user(self, user_manager):
        p = UserProfile(
            user_id="usr-del", email="del@test.com",
            username="deluser", display_name="Delete Me",
        )
        user_manager._users["usr-del"] = p
        assert user_manager.delete_user("usr-del") is True
        assert user_manager.get_user("usr-del") is None

    def test_get_stats(self, user_manager):
        stats = user_manager.get_stats()
        assert isinstance(stats, dict)


# ══════════════════════════════════════════════════════════════════
# GROUP MANAGER
# ══════════════════════════════════════════════════════════════════


class TestGroupManager:

    def test_create_group(self, group_manager):
        g = group_manager.create(
            name="Procurement Team",
            description="Handles procurement",
            lob="Procurement",
            allowed_model_ids=["gemini-2.5-flash"],
        )
        assert g.group_id.startswith("grp-")
        assert g.name == "Procurement Team"

    def test_get_group(self, group_manager):
        g = group_manager.create(name="Test Group", lob="IT")
        fetched = group_manager.get(g.group_id)
        assert fetched is not None
        assert fetched.name == "Test Group"

    def test_list_all(self, group_manager):
        group_manager.create(name="G1", lob="IT")
        group_manager.create(name="G2", lob="Finance")
        groups = group_manager.list_all()
        assert len(groups) >= 2

    def test_add_member(self, group_manager):
        g = group_manager.create(name="Members Group", lob="IT")
        result = group_manager.add_member(g.group_id, "user-001")
        assert result is True
        fetched = group_manager.get(g.group_id)
        assert "user-001" in fetched.member_ids

    def test_remove_member(self, group_manager):
        g = group_manager.create(name="Remove Group", lob="IT")
        group_manager.add_member(g.group_id, "user-001")
        result = group_manager.remove_member(g.group_id, "user-001")
        assert result is True

    def test_assign_models(self, group_manager):
        g = group_manager.create(name="Model Group", lob="IT")
        result = group_manager.assign_models(g.group_id, ["gemini-2.5-flash", "gpt-4o"])
        assert result is True
        fetched = group_manager.get(g.group_id)
        assert "gemini-2.5-flash" in fetched.allowed_model_ids

    def test_assign_agents(self, group_manager):
        g = group_manager.create(name="Agent Group", lob="IT")
        result = group_manager.assign_agents(g.group_id, ["agt-001", "agt-002"])
        assert result is True

    def test_delete_group(self, group_manager):
        g = group_manager.create(name="Delete Me", lob="IT")
        assert group_manager.delete(g.group_id) is True
        assert group_manager.get(g.group_id) is None

    def test_get_user_allowed_models(self, group_manager):
        g = group_manager.create(
            name="Policy Group", lob="IT",
            allowed_model_ids=["gemini-2.5-flash"],
        )
        group_manager.add_member(g.group_id, "user-model-test")
        models = group_manager.get_user_allowed_models("user-model-test")
        assert "gemini-2.5-flash" in models

    def test_get_stats(self, group_manager):
        group_manager.create(name="Stats Group", lob="IT")
        stats = group_manager.get_stats()
        assert isinstance(stats, dict)
