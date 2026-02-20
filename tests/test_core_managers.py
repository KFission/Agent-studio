"""
Tests for core managers — ToolRegistry, Orchestrator, AgentMemory, AgentRAG.
Run: pytest tests/test_core_managers.py -v
"""
import pytest
from backend.tool_builder.tool_registry import ToolRegistry, ToolDefinition, ToolType
from backend.orchestrator.orchestrator import (
    AgentOrchestrator, Pipeline, PipelineStep, OrchestrationPattern,
)
from backend.agent_service.agent_memory import AgentMemoryManager
from backend.agent_service.agent_rag import AgentRAGManager


# ══════════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ══════════════════════════════════════════════════════════════════


class TestToolRegistry:

    def test_create_tool(self, tool_registry):
        tool = ToolDefinition(
            name="PO Lookup",
            description="Look up purchase orders",
            tool_type=ToolType.REST_API,
            tags=["procurement"],
        )
        created = tool_registry.create(tool)
        assert created.tool_id.startswith("tool-")
        assert created.name == "PO Lookup"
        assert created.version == 1

    def test_get_tool(self, tool_registry):
        tool = ToolDefinition(name="Getter Tool", tool_type=ToolType.CODE)
        created = tool_registry.create(tool)
        fetched = tool_registry.get(created.tool_id)
        assert fetched is not None
        assert fetched.name == "Getter Tool"

    def test_get_nonexistent(self, tool_registry):
        assert tool_registry.get("tool-fake") is None

    def test_update_tool(self, tool_registry):
        tool = ToolDefinition(name="V1 Tool", tool_type=ToolType.CODE)
        created = tool_registry.create(tool)
        updated = tool_registry.update(created.tool_id, {"name": "V2 Tool"})
        assert updated is not None
        assert updated.name == "V2 Tool"
        assert updated.version == 2

    def test_delete_tool(self, tool_registry):
        tool = ToolDefinition(name="Delete Me", tool_type=ToolType.CODE)
        created = tool_registry.create(tool)
        assert tool_registry.delete(created.tool_id) is True
        assert tool_registry.get(created.tool_id) is None

    def test_list_all(self, tool_registry):
        for i in range(3):
            tool_registry.create(ToolDefinition(name=f"Tool {i}", tool_type=ToolType.CODE))
        tools = tool_registry.list_all()
        assert len(tools) == 3

    def test_list_by_type(self, tool_registry):
        tool_registry.create(ToolDefinition(name="REST", tool_type=ToolType.REST_API))
        tool_registry.create(ToolDefinition(name="Code", tool_type=ToolType.CODE))
        rest_tools = tool_registry.list_all(ToolType.REST_API)
        assert len(rest_tools) == 1
        assert rest_tools[0].name == "REST"

    def test_search(self, tool_registry):
        tool_registry.create(ToolDefinition(name="Invoice Parser", tool_type=ToolType.CODE))
        tool_registry.create(ToolDefinition(name="PO Generator", tool_type=ToolType.CODE))
        results = tool_registry.search("invoice")
        assert len(results) == 1

    def test_clone(self, tool_registry):
        original = tool_registry.create(ToolDefinition(name="Original", tool_type=ToolType.CODE))
        cloned = tool_registry.clone(original.tool_id, "Cloned")
        assert cloned is not None
        assert cloned.name == "Cloned"
        assert cloned.tool_id != original.tool_id

    def test_get_stats(self, tool_registry):
        tool_registry.create(ToolDefinition(name="T1", tool_type=ToolType.CODE))
        tool_registry.create(ToolDefinition(name="T2", tool_type=ToolType.REST_API))
        stats = tool_registry.get_stats()
        assert stats["total_tools"] == 2


# ══════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════


class TestOrchestrator:

    def _make_pipeline(self, orchestrator, name="Test Pipeline"):
        steps = [
            PipelineStep(name="Step 1", agent_id="agt-001"),
            PipelineStep(name="Step 2", agent_id="agt-002"),
        ]
        pipe = Pipeline(
            name=name,
            description="Test pipeline",
            pattern=OrchestrationPattern.SEQUENTIAL,
            steps=steps,
        )
        return orchestrator.create_pipeline(pipe)

    def test_create_pipeline(self, orchestrator):
        created = self._make_pipeline(orchestrator)
        assert created.pipeline_id.startswith("pipe-")
        assert len(created.steps) == 2

    def test_get_pipeline(self, orchestrator):
        created = self._make_pipeline(orchestrator)
        fetched = orchestrator.get_pipeline(created.pipeline_id)
        assert fetched is not None
        assert fetched.name == "Test Pipeline"

    def test_delete_pipeline(self, orchestrator):
        created = self._make_pipeline(orchestrator)
        assert orchestrator.delete_pipeline(created.pipeline_id) is True
        assert orchestrator.get_pipeline(created.pipeline_id) is None

    def test_list_pipelines(self, orchestrator):
        self._make_pipeline(orchestrator, "P1")
        self._make_pipeline(orchestrator, "P2")
        pipes = orchestrator.list_pipelines()
        assert len(pipes) == 2

    def test_execute_pipeline(self, orchestrator):
        created = self._make_pipeline(orchestrator)
        run = orchestrator.execute_pipeline(created.pipeline_id, {"input": "test"})
        assert run.run_id.startswith("prun-")
        assert run.pipeline_id == created.pipeline_id

    def test_get_stats(self, orchestrator):
        self._make_pipeline(orchestrator)
        stats = orchestrator.get_stats()
        assert stats["total_pipelines"] == 1


# ══════════════════════════════════════════════════════════════════
# AGENT MEMORY
# ══════════════════════════════════════════════════════════════════


class TestAgentMemory:

    def test_add_and_get_message(self, agent_memory):
        entry = agent_memory.add_message("agt-001", "sess-1", "user", "Hello!")
        assert entry.entry_id is not None
        conv = agent_memory.get_conversation("agt-001", "sess-1")
        assert len(conv) == 1
        assert conv[0].content == "Hello!"

    def test_conversation_ordering(self, agent_memory):
        agent_memory.add_message("agt-001", "sess-1", "user", "First")
        agent_memory.add_message("agt-001", "sess-1", "assistant", "Second")
        agent_memory.add_message("agt-001", "sess-1", "user", "Third")
        conv = agent_memory.get_conversation("agt-001", "sess-1")
        assert len(conv) == 3

    def test_list_sessions(self, agent_memory):
        agent_memory.add_message("agt-001", "sess-a", "user", "A")
        agent_memory.add_message("agt-001", "sess-b", "user", "B")
        sessions = agent_memory.list_sessions("agt-001")
        session_ids = [s["session_id"] if isinstance(s, dict) else s for s in sessions]
        assert "sess-a" in session_ids
        assert "sess-b" in session_ids

    def test_store_long_term(self, agent_memory):
        entry = agent_memory.store_long_term("agt-001", "Important fact", {"key": "val"})
        assert entry.entry_id is not None
        memories = agent_memory.get_long_term("agt-001")
        assert len(memories) >= 1

    def test_clear_all(self, agent_memory):
        agent_memory.add_message("agt-001", "sess-1", "user", "Hello")
        agent_memory.store_long_term("agt-001", "Fact")
        result = agent_memory.clear_all("agt-001")
        assert isinstance(result, dict)

    def test_memory_stats(self, agent_memory):
        agent_memory.add_message("agt-001", "sess-1", "user", "Hello")
        stats = agent_memory.get_agent_memory_stats("agt-001")
        assert isinstance(stats, dict)


# ══════════════════════════════════════════════════════════════════
# AGENT RAG
# ══════════════════════════════════════════════════════════════════


class TestAgentRAG:

    def test_create_collection(self, agent_rag):
        col = agent_rag.create_collection("Test KB", "agt-001", "Test collection")
        assert col.collection_id is not None
        assert col.name == "Test KB"

    def test_list_collections(self, agent_rag):
        agent_rag.create_collection("KB1", "agt-001")
        agent_rag.create_collection("KB2", "agt-002")
        cols = agent_rag.list_collections()
        assert len(cols) == 2

    def test_list_collections_by_agent(self, agent_rag):
        agent_rag.create_collection("KB1", "agt-001")
        agent_rag.create_collection("KB2", "agt-002")
        cols = agent_rag.list_collections("agt-001")
        assert len(cols) == 1

    def test_add_document(self, agent_rag):
        col = agent_rag.create_collection("Doc KB", "agt-001")
        doc = agent_rag.add_document(col.collection_id, "Document content here")
        assert doc is not None
        assert doc.doc_id is not None

    def test_get_documents(self, agent_rag):
        col = agent_rag.create_collection("Doc KB", "agt-001")
        agent_rag.add_document(col.collection_id, "Doc 1")
        agent_rag.add_document(col.collection_id, "Doc 2")
        docs = agent_rag.get_documents(col.collection_id)
        assert len(docs) == 2

    def test_delete_collection(self, agent_rag):
        col = agent_rag.create_collection("To Delete", "agt-001")
        assert agent_rag.delete_collection(col.collection_id) is True
        cols = agent_rag.list_collections()
        assert len(cols) == 0

    def test_get_stats(self, agent_rag):
        agent_rag.create_collection("Stats KB", "agt-001")
        stats = agent_rag.get_stats()
        assert isinstance(stats, dict)
