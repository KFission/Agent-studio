"""
End-to-end test: DB-backed agent CRUD + credential store + agent invocation.
Run with: .venv/bin/python -m pytest tests/test_db_e2e.py -v
"""
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.config.settings import settings
from backend.db.base import Base
from backend.db.models import AgentModel, ProviderCredentialModel  # noqa: F401
from backend.db.agent_repository import AgentRepository
from backend.db.credential_store import CredentialStore
from backend.agent_service.agent_registry import (
    AgentDefinition, AgentStatus, ModelConfig, RAGConfig,
    MemoryConfig, AccessControl,
)


# ── Test fixtures ────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session():
    """Create a fresh test DB session with tables."""
    engine = create_async_engine(settings.database_url, echo=False, connect_args={"ssl": "disable"})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()

    # Cleanup: drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Agent CRUD Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_get_agent(db_session):
    """Create an agent in Postgres and retrieve it."""
    repo = AgentRepository(db_session)

    agent = AgentDefinition(
        name="Test Procurement Agent",
        description="Handles procurement queries using Vertex AI",
        tags=["procurement", "test"],
        model_config=ModelConfig(model_id="gemini-2.5-flash", temperature=0.3, max_tokens=2000),
        context="You are a helpful procurement assistant.",
        access_control=AccessControl(owner_id="test-user"),
    )

    created = await repo.create(agent)
    assert created.agent_id.startswith("agt-")
    assert created.name == "Test Procurement Agent"

    # Retrieve
    fetched = await repo.get(created.agent_id)
    assert fetched is not None
    assert fetched.name == "Test Procurement Agent"
    assert fetched.model_config_.model_id == "gemini-2.5-flash"
    assert fetched.context == "You are a helpful procurement assistant."
    assert fetched.tags == ["procurement", "test"]
    print(f"✓ Created and fetched agent: {fetched.agent_id}")


@pytest.mark.asyncio
async def test_list_agents(db_session):
    """Create multiple agents and list them."""
    repo = AgentRepository(db_session)

    for i in range(3):
        agent = AgentDefinition(
            name=f"Agent {i}",
            description=f"Test agent number {i}",
            model_config=ModelConfig(model_id="gemini-2.0-flash"),
        )
        await repo.create(agent)

    agents = await repo.list_all()
    assert len(agents) == 3
    print(f"✓ Listed {len(agents)} agents")


@pytest.mark.asyncio
async def test_update_agent(db_session):
    """Update an agent's fields."""
    repo = AgentRepository(db_session)

    agent = AgentDefinition(name="Original Name", model_config=ModelConfig(model_id="gemini-2.5-flash"))
    created = await repo.create(agent)

    updated = await repo.update(created.agent_id, {"name": "Updated Name", "description": "Now with description"})
    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.description == "Now with description"
    assert updated.version == 2
    print(f"✓ Updated agent to v{updated.version}")


@pytest.mark.asyncio
async def test_delete_agent(db_session):
    """Delete an agent."""
    repo = AgentRepository(db_session)

    agent = AgentDefinition(name="To Delete", model_config=ModelConfig(model_id="gemini-2.0-flash"))
    created = await repo.create(agent)

    deleted = await repo.delete(created.agent_id)
    assert deleted is True

    fetched = await repo.get(created.agent_id)
    assert fetched is None
    print(f"✓ Deleted agent {created.agent_id}")


# ── Credential Store Tests ───────────────────────────────────────

@pytest.mark.asyncio
async def test_credential_store_encrypt_decrypt(db_session):
    """Store an encrypted credential and retrieve it."""
    store = CredentialStore(db_session)

    fake_sa_json = {
        "type": "service_account",
        "project_id": "gcp-jai-platform-dev",
        "private_key_id": "abc123",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nFAKEKEY\n-----END RSA PRIVATE KEY-----\n",
        "client_email": "jai-agent@gcp-jai-platform-dev.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    result = await store.store(
        name="Vertex AI - Dev",
        provider="google",
        credential_data=fake_sa_json,
    )
    assert result["id"].startswith("cred-")
    assert result["provider"] == "google"
    assert result["display_metadata"]["project_id"] == "gcp-jai-platform-dev"
    print(f"✓ Stored credential: {result['id']}")

    # Retrieve and decrypt
    decrypted = await store.get_decrypted(result["id"])
    assert decrypted is not None
    assert decrypted["project_id"] == "gcp-jai-platform-dev"
    assert decrypted["private_key"].startswith("-----BEGIN RSA PRIVATE KEY-----")
    print(f"✓ Decrypted credential matches original")

    # Metadata should NOT contain secrets
    meta = await store.get_metadata(result["id"])
    assert "private_key" not in str(meta)
    assert meta["display_metadata"]["project_id"] == "gcp-jai-platform-dev"
    print(f"✓ Metadata does not leak secrets")


@pytest.mark.asyncio
async def test_agent_with_credential(db_session):
    """Create a credential, then create an agent linked to it."""
    store = CredentialStore(db_session)
    repo = AgentRepository(db_session)

    cred = await store.store(
        name="Test SA",
        provider="google",
        credential_data={"type": "service_account", "project_id": "test-project"},
    )

    agent = AgentDefinition(
        name="Agent with Creds",
        model_config=ModelConfig(model_id="gemini-2.5-flash"),
        context="You are a test agent.",
    )
    created = await repo.create(agent, credential_id=cred["id"])

    # Verify the link
    data = await repo.get_with_credential_id(created.agent_id)
    assert data is not None
    assert data["credential_id"] == cred["id"]
    assert data["agent"].name == "Agent with Creds"
    print(f"✓ Agent {created.agent_id} linked to credential {cred['id']}")


@pytest.mark.asyncio
async def test_stats(db_session):
    """Verify stats work."""
    repo = AgentRepository(db_session)

    agent = AgentDefinition(name="Stats Agent", model_config=ModelConfig(model_id="gemini-2.0-flash"))
    await repo.create(agent)

    stats = await repo.get_stats()
    assert stats["total"] == 1
    assert stats["by_status"]["draft"] == 1
    print(f"✓ Stats: {stats}")
