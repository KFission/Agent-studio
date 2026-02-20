"""
Shared fixtures for JAI Agent OS test suite.
"""
import sys
import os
import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set env vars before any imports that read them — ENVIRONMENT=dev bypasses auth
os.environ["ENVIRONMENT"] = "dev"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "")
os.environ.setdefault("LANGFUSE_HOST", "")
os.environ.setdefault("LANGCHAIN_API_KEY", "")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")


@pytest.fixture
def agent_registry():
    """Fresh AgentRegistry instance (in-memory, no DB)."""
    from backend.agent_service.agent_registry import AgentRegistry
    return AgentRegistry()


@pytest.fixture
def environment_manager():
    """Fresh EnvironmentManager instance (in-memory, no DB)."""
    from backend.environments.environment_manager import EnvironmentManager
    return EnvironmentManager()


@pytest.fixture
def tool_registry():
    """Fresh ToolRegistry instance."""
    from backend.tool_builder.tool_registry import ToolRegistry
    return ToolRegistry()


@pytest.fixture
def orchestrator():
    """Fresh AgentOrchestrator instance."""
    from backend.orchestrator.orchestrator import AgentOrchestrator
    return AgentOrchestrator()


@pytest.fixture
def agent_memory():
    """Fresh AgentMemoryManager instance."""
    from backend.agent_service.agent_memory import AgentMemoryManager
    return AgentMemoryManager()


@pytest.fixture
def agent_rag():
    """Fresh AgentRAGManager instance."""
    from backend.agent_service.agent_rag import AgentRAGManager
    return AgentRAGManager()


@pytest.fixture
def rbac_manager():
    """Fresh RBACManager instance."""
    from backend.auth.rbac import RBACManager
    return RBACManager()


@pytest.fixture
def user_manager():
    """Fresh UserManager instance."""
    from backend.auth.user_manager import UserManager
    return UserManager()


@pytest.fixture
def group_manager():
    """Fresh GroupManager instance."""
    from backend.auth.group_manager import GroupManager
    return GroupManager()
