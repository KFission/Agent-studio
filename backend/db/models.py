"""
SQLAlchemy ORM models for the Agent Studio platform.
Maps to PostgreSQL tables via Alembic migrations.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Index, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


# ── Agents ─────────────────────────────────────────────────────────────────────

class AgentModel(Base):
    """Persisted agent definition — core table."""
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"agt-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)

    # Core configuration — stored as JSONB for flexibility
    model_config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    context: Mapped[str] = mapped_column(Text, default="")
    prompt_template_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Per-agent feature configs
    rag_config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    memory_config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    db_config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    tools_json: Mapped[dict] = mapped_column(JSONB, default=list)

    # Serving
    endpoint_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    access_control_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Graph reference
    graph_manifest_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(128), default="")
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    # FK to credential used for LLM provider
    credential_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("provider_credentials.id"), nullable=True
    )
    credential: Mapped["ProviderCredentialModel | None"] = relationship(
        back_populates="agents", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_agents_status_updated", "status", "updated_at"),
        Index("ix_agents_created_by", "created_by"),
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name!r} status={self.status}>"


# ── Provider Credentials ───────────────────────────────────────────────────────

class ProviderCredentialModel(Base):
    """
    Stores LLM provider credentials (e.g. Vertex AI service account JSON).
    The credential_blob is encrypted at rest using Fernet symmetric encryption.
    """
    __tablename__ = "provider_credentials"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"cred-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Encrypted JSON blob (Fernet-encrypted service account JSON, API key, etc.)
    credential_blob: Mapped[str] = mapped_column(Text, nullable=False)
    # Unencrypted metadata for display (project_id, region, etc. — no secrets)
    display_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(128), default="")

    agents: Mapped[list["AgentModel"]] = relationship(
        back_populates="credential", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Credential id={self.id} name={self.name!r} provider={self.provider}>"


# ── Users ─────────────────────────────────────────────────────────────────────

class UserModel(Base):
    """Platform user with hashed password for local auth."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uuid.uuid4().hex[:16]
    )
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    first_name: Mapped[str] = mapped_column(String(128), default="")
    last_name: Mapped[str] = mapped_column(String(128), default="")
    display_name: Mapped[str] = mapped_column(String(256), default="")
    avatar_url: Mapped[str] = mapped_column(Text, default="")
    tenant_id: Mapped[str] = mapped_column(String(64), default="default")
    roles: Mapped[dict] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


# ── Tools ─────────────────────────────────────────────────────────────────────

class ToolModel(Base):
    """Persisted tool definition."""
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"tool-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    tool_type: Mapped[str] = mapped_column(String(32), default="api")
    category: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    endpoints_json: Mapped[dict] = mapped_column(JSONB, default=list)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_platform_tool: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(128), default="system")
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    def __repr__(self) -> str:
        return f"<Tool id={self.id} name={self.name!r} type={self.tool_type}>"


# ── Prompt Templates ──────────────────────────────────────────────────────────

class PromptTemplateModel(Base):
    """Persisted prompt template with versioned content."""
    __tablename__ = "prompt_templates"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"prompt-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="custom")
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[dict] = mapped_column(JSONB, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(128), default="system")

    def __repr__(self) -> str:
        return f"<Prompt id={self.id} name={self.name!r}>"


# ── Tenants ───────────────────────────────────────────────────────────────────

class GuardrailRuleModel(Base):
    """Persisted guardrail rule definition."""
    __tablename__ = "guardrail_rules"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"gr-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False, default="custom", index=True)
    scope: Mapped[str] = mapped_column(String(32), default="global")
    action: Mapped[str] = mapped_column(String(32), default="block")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    applies_to: Mapped[str] = mapped_column(String(32), default="both")
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    agent_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    group_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    is_deployed: Mapped[bool] = mapped_column(Boolean, default=False)
    times_triggered: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(128), default="admin")

    def __repr__(self) -> str:
        return f"<GuardrailRule id={self.id} name={self.name!r} type={self.rule_type}>"


# ── LLM Integrations ───────────────────────────────────────────────────────────

class IntegrationModel(Base):
    """Persisted LLM provider integration (API key, service account, etc.)."""
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"int-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # Auth — encrypted API key or service account JSON
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    api_key_masked: Mapped[str] = mapped_column(String(64), default="")
    auth_type: Mapped[str] = mapped_column(String(32), default="api_key")  # api_key | service_account
    service_account_json: Mapped[dict] = mapped_column(JSONB, default=dict)  # legacy — unencrypted
    service_account_json_encrypted: Mapped[str] = mapped_column(Text, default="")  # Fernet-encrypted
    endpoint_url: Mapped[str] = mapped_column(Text, default="")
    project_id: Mapped[str] = mapped_column(String(256), default="")
    # Model config
    default_model: Mapped[str] = mapped_column(String(256), default="")
    allowed_models: Mapped[dict] = mapped_column(JSONB, default=list)
    registered_models: Mapped[dict] = mapped_column(JSONB, default=list)  # models registered in ModelLibrary
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=0)
    # Group assignment
    assigned_group_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    # Status
    status: Mapped[str] = mapped_column(String(32), default="active")
    last_tested: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    # Metadata
    created_by: Mapped[str] = mapped_column(String(128), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    def __repr__(self) -> str:
        return f"<Integration id={self.id} name={self.name!r} provider={self.provider}>"


# ── Threads & Messages ────────────────────────────────────────────────────────

class ThreadModel(Base):
    """Persisted conversation thread."""
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"thread-{uuid.uuid4().hex[:10]}"
    )
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant-default", index=True)
    user_id: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(512), default="New conversation")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    interrupt_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages: Mapped[list["ThreadMessageModel"]] = relationship(
        back_populates="thread", lazy="selectin", cascade="all, delete-orphan",
        order_by="ThreadMessageModel.created_at",
    )

    __table_args__ = (
        Index("ix_threads_agent_tenant", "agent_id", "tenant_id"),
        Index("ix_threads_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Thread id={self.id} agent={self.agent_id} status={self.status}>"


class ThreadMessageModel(Base):
    """Persisted message within a conversation thread."""
    __tablename__ = "thread_messages"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"msg-{uuid.uuid4().hex[:8]}"
    )
    thread_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    content: Mapped[str] = mapped_column(Text, default="")
    tool_calls_json: Mapped[dict] = mapped_column(JSONB, default=list)
    tool_call_id: Mapped[str] = mapped_column(String(128), default="")
    name: Mapped[str] = mapped_column(String(128), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    thread: Mapped["ThreadModel"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_thread_messages_thread_created", "thread_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} thread={self.thread_id} role={self.role}>"


# ── Usage Records ─────────────────────────────────────────────────────────────

class UsageRecordModel(Base):
    """Persisted LLM usage record for cost tracking and billing."""
    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"ur-{uuid.uuid4().hex[:10]}"
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    group_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    lob: Mapped[str] = mapped_column(String(128), default="")
    user_id: Mapped[str] = mapped_column(String(64), default="")
    agent_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    model_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    provider: Mapped[str] = mapped_column(String(64), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(32), default="success")
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("ix_usage_records_group_ts", "group_id", "timestamp"),
        Index("ix_usage_records_agent_ts", "agent_id", "timestamp"),
        Index("ix_usage_records_model_ts", "model_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<UsageRecord id={self.id} model={self.model_id} cost=${self.cost_usd:.4f}>"


class TenantModel(Base):
    """Multi-tenant configuration."""
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"tenant-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(32), default="enterprise")
    owner_email: Mapped[str] = mapped_column(String(256), default="")
    domain: Mapped[str] = mapped_column(String(256), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    quota_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    allowed_providers: Mapped[dict] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name!r} tier={self.tier}>"


# ── Groups ───────────────────────────────────────────────────────────────────

class GroupModel(Base):
    """Team / Line-of-Business group for RBAC and cost attribution."""
    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"grp-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    lob: Mapped[str] = mapped_column(String(128), default="", index=True)
    owner_id: Mapped[str] = mapped_column(String(128), default="")
    member_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    allowed_model_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    allowed_agent_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    assigned_roles: Mapped[dict] = mapped_column(JSONB, default=list)
    monthly_budget_usd: Mapped[float] = mapped_column(Float, default=0)
    daily_token_limit: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.name!r} lob={self.lob}>"


# ── Pipelines ────────────────────────────────────────────────────────────────

class PipelineModel(Base):
    """Orchestration pipeline connecting multiple agents."""
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"pipe-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    pattern: Mapped[str] = mapped_column(String(32), default="sequential")
    steps_json: Mapped[dict] = mapped_column(JSONB, default=list)
    supervisor_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    owner_id: Mapped[str] = mapped_column(String(128), default="")
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Pipeline id={self.id} name={self.name!r} pattern={self.pattern}>"


class PipelineRunModel(Base):
    """Record of a pipeline execution."""
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"prun-{uuid.uuid4().hex[:8]}"
    )
    pipeline_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    pipeline_name: Mapped[str] = mapped_column(String(256), default="")
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    pattern: Mapped[str] = mapped_column(String(32), default="")
    steps_completed: Mapped[int] = mapped_column(Integer, default=0)
    steps_total: Mapped[int] = mapped_column(Integer, default=0)
    step_results_json: Mapped[dict] = mapped_column(JSONB, default=list)
    input_data_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_data_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_latency_ms: Mapped[float] = mapped_column(Float, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_pipeline_runs_pipeline_started", "pipeline_id", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<PipelineRun id={self.id} pipeline={self.pipeline_id} status={self.status}>"


# ── Inbox Items ──────────────────────────────────────────────────────────────

class InboxItemModel(Base):
    """Human-in-the-loop approval/review inbox item."""
    __tablename__ = "inbox_items"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"inbox-{uuid.uuid4().hex[:8]}"
    )
    thread_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    agent_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant-default", index=True)
    user_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    interrupt_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    thread_title: Mapped[str] = mapped_column(String(512), default="")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_preview: Mapped[str] = mapped_column(Text, default="")
    action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolved_by: Mapped[str] = mapped_column(String(128), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_inbox_items_tenant_status", "tenant_id", "status"),
        Index("ix_inbox_items_agent_status", "agent_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<InboxItem id={self.id} agent={self.agent_id} status={self.status}>"


# ── Memory Entries ───────────────────────────────────────────────────────────

class MemoryEntryModel(Base):
    """Agent memory entry (short-term or long-term)."""
    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uuid.uuid4().hex[:12]
    )
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(128), default="default", index=True)
    role: Mapped[str] = mapped_column(String(32), default="user")
    content: Mapped[str] = mapped_column(Text, default="")
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_memory_entries_agent_session", "agent_id", "session_id"),
        Index("ix_memory_entries_agent_type", "agent_id", "memory_type"),
    )

    def __repr__(self) -> str:
        return f"<MemoryEntry id={self.id} agent={self.agent_id} type={self.memory_type}>"


# ── RAG Collections & Documents ──────────────────────────────────────────────

class RAGCollectionModel(Base):
    """RAG document collection."""
    __tablename__ = "rag_collections"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"col-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    embedding_model: Mapped[str] = mapped_column(String(128), default="text-embedding-004")
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<RAGCollection id={self.id} name={self.name!r}>"


class RAGDocumentModel(Base):
    """Document within a RAG collection."""
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uuid.uuid4().hex[:12]
    )
    collection_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("rag_collections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    content: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_rag_documents_collection", "collection_id"),
    )

    def __repr__(self) -> str:
        return f"<RAGDocument id={self.id} collection={self.collection_id}>"


# ── Environment Management ────────────────────────────────────────────────

class EnvironmentConfigModel(Base):
    __tablename__ = "environment_configs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)  # tenant_id:env_id
    env_id: Mapped[str] = mapped_column(String(20), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant-default")
    label: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    variables_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    locked_by: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_env_configs_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<EnvironmentConfig id={self.id} env={self.env_id}>"


# ── Knowledge Bases ──────────────────────────────────────────────────────────

class KnowledgeBaseModel(Base):
    """Vertex AI Search datastore backed by a GCS bucket."""
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"kb-{uuid.uuid4().hex[:8]}"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # GCS bucket
    bucket_name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    # Vertex AI Discovery Engine datastore
    datastore_id: Mapped[str] = mapped_column(String(256), nullable=False)
    datastore_name: Mapped[str] = mapped_column(String(256), nullable=False)
    # Chunking config
    chunk_size: Mapped[int] = mapped_column(Integer, default=500)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=100)
    # Parser
    parser_type: Mapped[str] = mapped_column(String(64), default="layout")
    # GCP
    gcp_project_id: Mapped[str] = mapped_column(String(256), nullable=False)
    gcp_location: Mapped[str] = mapped_column(String(64), default="global")
    # Status
    status: Mapped[str] = mapped_column(String(32), default="creating", index=True)
    # Counts
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    total_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    # Ownership
    created_by: Mapped[str] = mapped_column(String(128), default="")
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Metadata
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    files: Mapped[list["FileUploadModel"]] = relationship(
        back_populates="knowledge_base", lazy="selectin", cascade="all, delete-orphan",
        order_by="FileUploadModel.created_at.desc()",
    )

    __table_args__ = (
        Index("ix_knowledge_bases_created_by", "created_by"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase id={self.id} name={self.name!r} bucket={self.bucket_name}>"


class FileUploadModel(Base):
    """Tracks every file uploaded to any knowledge base."""
    __tablename__ = "file_uploads"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"file-{uuid.uuid4().hex[:8]}"
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Original file info
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), default="")
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    # GCS location
    gcs_uri: Mapped[str] = mapped_column(Text, nullable=False)
    # Processing status: pending | processing | indexed | failed
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    # Chunking results
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    # Who uploaded
    uploaded_by: Mapped[str] = mapped_column(String(128), default="")
    # Metadata
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    knowledge_base: Mapped["KnowledgeBaseModel"] = relationship(back_populates="files")

    __table_args__ = (
        Index("ix_file_uploads_kb_status", "knowledge_base_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<FileUpload id={self.id} file={self.file_name!r} kb={self.knowledge_base_id}>"


class PromotionRecordModel(Base):
    __tablename__ = "promotion_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant-default")
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_name: Mapped[str] = mapped_column(String(256), default="")
    from_env: Mapped[str] = mapped_column(String(20), nullable=False)
    to_env: Mapped[str] = mapped_column(String(20), nullable=False)
    from_version: Mapped[int] = mapped_column(Integer, default=0)
    to_version: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    requested_by: Mapped[str] = mapped_column(String(128), default="")
    approved_by: Mapped[str] = mapped_column(String(128), default="")
    rejected_by: Mapped[str] = mapped_column(String(128), default="")
    rejection_reason: Mapped[str] = mapped_column(Text, default="")
    snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    diff_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    deployed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_promotions_tenant_env", "tenant_id", "to_env"),
        Index("ix_promotions_status", "status"),
        Index("ix_promotions_asset", "asset_type", "asset_id"),
    )

    def __repr__(self) -> str:
        return f"<PromotionRecord id={self.id} {self.from_env}→{self.to_env} status={self.status}>"
