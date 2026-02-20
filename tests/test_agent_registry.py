"""
Tests for AgentRegistry — CRUD, versioning, rollback, diff.
Run: pytest tests/test_agent_registry.py -v
"""
import pytest
from backend.agent_service.agent_registry import (
    AgentRegistry, AgentDefinition, AgentStatus, ModelConfig,
    RAGConfig, MemoryConfig, AccessControl,
)


# ── CRUD ─────────────────────────────────────────────────────────


class TestAgentCRUD:

    def test_create_agent(self, agent_registry):
        agent = AgentDefinition(
            name="Procurement Bot",
            description="Handles procurement queries",
            tags=["procurement"],
            context="You are a procurement assistant.",
        )
        created = agent_registry.create(agent)
        assert created.agent_id.startswith("agt-")
        assert created.name == "Procurement Bot"
        assert created.version == 1
        assert created.status == AgentStatus.DRAFT

    def test_get_agent(self, agent_registry):
        agent = AgentDefinition(name="Getter")
        created = agent_registry.create(agent)
        fetched = agent_registry.get(created.agent_id)
        assert fetched is not None
        assert fetched.name == "Getter"

    def test_get_nonexistent_returns_none(self, agent_registry):
        assert agent_registry.get("agt-nonexistent") is None

    def test_update_agent(self, agent_registry):
        agent = AgentDefinition(name="Original")
        created = agent_registry.create(agent)
        updated = agent_registry.update(created.agent_id, {"name": "Updated", "description": "New desc"})
        assert updated is not None
        assert updated.name == "Updated"
        assert updated.description == "New desc"
        assert updated.version == 2

    def test_update_nonexistent_returns_none(self, agent_registry):
        assert agent_registry.update("agt-nonexistent", {"name": "X"}) is None

    def test_delete_agent(self, agent_registry):
        agent = AgentDefinition(name="To Delete")
        created = agent_registry.create(agent)
        assert agent_registry.delete(created.agent_id) is True
        assert agent_registry.get(created.agent_id) is None

    def test_delete_nonexistent_returns_false(self, agent_registry):
        assert agent_registry.delete("agt-nonexistent") is False

    def test_set_status(self, agent_registry):
        agent = AgentDefinition(name="Status Test")
        created = agent_registry.create(agent)
        result = agent_registry.set_status(created.agent_id, AgentStatus.ACTIVE)
        assert result is not None
        assert result.status == AgentStatus.ACTIVE

    def test_list_all(self, agent_registry):
        for i in range(3):
            agent_registry.create(AgentDefinition(name=f"Agent {i}"))
        agents = agent_registry.list_all()
        assert len(agents) == 3

    def test_list_all_by_status(self, agent_registry):
        a1 = agent_registry.create(AgentDefinition(name="Draft Agent"))
        a2 = agent_registry.create(AgentDefinition(name="Active Agent"))
        agent_registry.set_status(a2.agent_id, AgentStatus.ACTIVE)
        drafts = agent_registry.list_all(status=AgentStatus.DRAFT)
        assert len(drafts) == 1
        assert drafts[0].name == "Draft Agent"

    def test_search(self, agent_registry):
        agent_registry.create(AgentDefinition(name="Procurement Helper", tags=["procurement"]))
        agent_registry.create(AgentDefinition(name="Sourcing Bot", tags=["sourcing"]))
        results = agent_registry.search("procurement")
        assert len(results) == 1
        assert results[0].name == "Procurement Helper"

    def test_get_stats(self, agent_registry):
        agent_registry.create(AgentDefinition(name="A1"))
        agent_registry.create(AgentDefinition(name="A2", rag_config=RAGConfig(enabled=True)))
        stats = agent_registry.get_stats()
        assert stats["total_agents"] == 2
        assert stats["with_rag"] == 1


# ── Versioning ───────────────────────────────────────────────────


class TestAgentVersioning:

    def test_versions_created_on_update(self, agent_registry):
        agent = agent_registry.create(AgentDefinition(name="V1"))
        agent_registry.update(agent.agent_id, {"name": "V2"})
        agent_registry.update(agent.agent_id, {"name": "V3"})
        versions = agent_registry.get_versions(agent.agent_id)
        assert len(versions) >= 2

    def test_get_version_detail(self, agent_registry):
        agent = agent_registry.create(AgentDefinition(name="V1 Name"))
        agent_registry.update(agent.agent_id, {"name": "V2 Name"})
        # Version 1 should have original name
        v1 = agent_registry.get_version_detail(agent.agent_id, 1)
        assert v1 is not None
        assert v1["name"] == "V1 Name"

    def test_get_version_detail_nonexistent(self, agent_registry):
        agent = agent_registry.create(AgentDefinition(name="Solo"))
        assert agent_registry.get_version_detail(agent.agent_id, 999) is None

    def test_rollback_to_version(self, agent_registry):
        agent = agent_registry.create(AgentDefinition(name="Original Name", description="V1 desc"))
        agent_registry.update(agent.agent_id, {"name": "Changed Name", "description": "V2 desc"})
        # Current should be V2
        current = agent_registry.get(agent.agent_id)
        assert current.name == "Changed Name"
        assert current.version == 2
        # Rollback to V1
        restored = agent_registry.rollback_to_version(agent.agent_id, 1, "admin")
        assert restored is not None
        assert restored.name == "Original Name"
        assert restored.version == 3  # new version created
        assert restored.metadata.get("rollback_from") == 1

    def test_rollback_nonexistent_version(self, agent_registry):
        agent = agent_registry.create(AgentDefinition(name="No Rollback"))
        assert agent_registry.rollback_to_version(agent.agent_id, 999) is None

    def test_rollback_nonexistent_agent(self, agent_registry):
        assert agent_registry.rollback_to_version("agt-fake", 1) is None

    def test_diff_versions(self, agent_registry):
        agent = agent_registry.create(AgentDefinition(name="V1", description="Desc 1", tags=["a"]))
        agent_registry.update(agent.agent_id, {"name": "V2", "description": "Desc 2", "tags": ["b"]})
        diff = agent_registry.diff_versions(agent.agent_id, 1, 2)
        assert diff is not None
        assert diff["total_changes"] > 0
        field_names = [c["field"] for c in diff["changes"]]
        assert "name" in field_names

    def test_diff_nonexistent_version(self, agent_registry):
        agent = agent_registry.create(AgentDefinition(name="Solo"))
        assert agent_registry.diff_versions(agent.agent_id, 1, 999) is None

    def test_diff_nonexistent_agent(self, agent_registry):
        assert agent_registry.diff_versions("agt-fake", 1, 2) is None


# ── Clone ────────────────────────────────────────────────────────


class TestAgentClone:

    @pytest.mark.asyncio
    async def test_clone_agent(self, agent_registry):
        original = agent_registry.create(AgentDefinition(
            name="Original", description="To be cloned", tags=["src"]
        ))
        cloned = await agent_registry.clone_async(original.agent_id, "Cloned Agent")
        assert cloned is not None
        assert cloned.name == "Cloned Agent"
        assert cloned.agent_id != original.agent_id
        assert cloned.version == 1
        assert cloned.status == AgentStatus.DRAFT

    @pytest.mark.asyncio
    async def test_clone_nonexistent(self, agent_registry):
        result = await agent_registry.clone_async("agt-fake", "Clone")
        assert result is None
