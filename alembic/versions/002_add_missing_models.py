"""Add missing models (users, tools, prompts, threads, etc.)

Revision ID: 002
Revises: 001
Create Date: 2026-02-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(128), nullable=False, unique=True),
        sa.Column("email", sa.String(256), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("first_name", sa.String(128), server_default=""),
        sa.Column("last_name", sa.String(128), server_default=""),
        sa.Column("display_name", sa.String(256), server_default=""),
        sa.Column("avatar_url", sa.Text, server_default=""),
        sa.Column("tenant_id", sa.String(64), server_default="default"),
        sa.Column("roles", JSONB, server_default="[]"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("preferences", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime, nullable=True),
        sa.Column("metadata_json", JSONB, server_default="{}"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── Tenants ───────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("tier", sa.String(32), server_default="enterprise"),
        sa.Column("owner_email", sa.String(256), server_default=""),
        sa.Column("domain", sa.String(256), server_default=""),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("settings_json", JSONB, server_default="{}"),
        sa.Column("quota_json", JSONB, server_default="{}"),
        sa.Column("allowed_providers", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # ── Tools ─────────────────────────────────────────────────────────────────
    op.create_table(
        "tools",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("tool_type", sa.String(32), server_default="api"),
        sa.Column("category", sa.String(64), server_default=""),
        sa.Column("status", sa.String(32), server_default="active"),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("config_json", JSONB, server_default="{}"),
        sa.Column("endpoints_json", JSONB, server_default="[]"),
        sa.Column("is_public", sa.Boolean, server_default="true"),
        sa.Column("is_platform_tool", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(128), server_default="system"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
    )
    op.create_index("ix_tools_name", "tools", ["name"])
    op.create_index("ix_tools_status", "tools", ["status"])

    # ── Prompt Templates ──────────────────────────────────────────────────────
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("category", sa.String(64), server_default="custom"),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("variables", JSONB, server_default="[]"),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("is_builtin", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(128), server_default="system"),
    )
    op.create_index("ix_prompt_templates_name", "prompt_templates", ["name"])

    # ── Guardrail Rules ───────────────────────────────────────────────────────
    op.create_table(
        "guardrail_rules",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("rule_type", sa.String(32), nullable=False, server_default="custom"),
        sa.Column("scope", sa.String(32), server_default="global"),
        sa.Column("action", sa.String(32), server_default="block"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("applies_to", sa.String(32), server_default="both"),
        sa.Column("config_json", JSONB, server_default="{}"),
        sa.Column("agent_ids", JSONB, server_default="[]"),
        sa.Column("group_ids", JSONB, server_default="[]"),
        sa.Column("is_deployed", sa.Boolean, server_default="false"),
        sa.Column("times_triggered", sa.Integer, server_default="0"),
        sa.Column("last_triggered", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(128), server_default="admin"),
    )
    op.create_index("ix_guardrail_rules_name", "guardrail_rules", ["name"])
    op.create_index("ix_guardrail_rules_rule_type", "guardrail_rules", ["rule_type"])

    # ── LLM Integrations ──────────────────────────────────────────────────────
    op.create_table(
        "integrations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("api_key_encrypted", sa.Text, server_default=""),
        sa.Column("api_key_masked", sa.String(64), server_default=""),
        sa.Column("auth_type", sa.String(32), server_default="api_key"),
        sa.Column("service_account_json", JSONB, server_default="{}"),
        sa.Column("service_account_json_encrypted", sa.Text, server_default=""),
        sa.Column("endpoint_url", sa.Text, server_default=""),
        sa.Column("project_id", sa.String(256), server_default=""),
        sa.Column("default_model", sa.String(256), server_default=""),
        sa.Column("allowed_models", JSONB, server_default="[]"),
        sa.Column("registered_models", JSONB, server_default="[]"),
        sa.Column("rate_limit_rpm", sa.Integer, server_default="0"),
        sa.Column("assigned_group_ids", JSONB, server_default="[]"),
        sa.Column("status", sa.String(32), server_default="active"),
        sa.Column("last_tested", sa.DateTime, nullable=True),
        sa.Column("last_error", sa.Text, server_default=""),
        sa.Column("created_by", sa.String(128), server_default="admin"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("metadata_json", JSONB, server_default="{}"),
    )
    op.create_index("ix_integrations_provider", "integrations", ["provider"])

    # ── Threads ───────────────────────────────────────────────────────────────
    op.create_table(
        "threads",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(64), server_default="tenant-default"),
        sa.Column("user_id", sa.String(64), server_default=""),
        sa.Column("title", sa.String(512), server_default="New conversation"),
        sa.Column("status", sa.String(32), server_default="active"),
        sa.Column("config_json", JSONB, server_default="{}"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("interrupt_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_threads_agent_tenant", "threads", ["agent_id", "tenant_id"])
    op.create_index("ix_threads_user", "threads", ["user_id"])
    op.create_index("ix_threads_status", "threads", ["status"])

    # ── Thread Messages ───────────────────────────────────────────────────────
    op.create_table(
        "thread_messages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("thread_id", sa.String(64), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="user"),
        sa.Column("content", sa.Text, server_default=""),
        sa.Column("tool_calls_json", JSONB, server_default="[]"),
        sa.Column("tool_call_id", sa.String(128), server_default=""),
        sa.Column("name", sa.String(128), server_default=""),
        sa.Column("model", sa.String(128), server_default=""),
        sa.Column("tokens", sa.Integer, server_default="0"),
        sa.Column("latency_ms", sa.Float, server_default="0.0"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_thread_messages_thread_created", "thread_messages", ["thread_id", "created_at"])
    op.create_foreign_key(
        "fk_thread_messages_thread_id", "thread_messages", "threads", ["thread_id"], ["id"], ondelete="CASCADE"
    )

    # ── Usage Records ─────────────────────────────────────────────────────────
    op.create_table(
        "usage_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("timestamp", sa.DateTime, server_default=sa.func.now()),
        sa.Column("group_id", sa.String(64), server_default=""),
        sa.Column("lob", sa.String(128), server_default=""),
        sa.Column("user_id", sa.String(64), server_default=""),
        sa.Column("agent_id", sa.String(64), server_default=""),
        sa.Column("model_id", sa.String(128), server_default=""),
        sa.Column("provider", sa.String(64), server_default=""),
        sa.Column("input_tokens", sa.Integer, server_default="0"),
        sa.Column("output_tokens", sa.Integer, server_default="0"),
        sa.Column("total_tokens", sa.Integer, server_default="0"),
        sa.Column("cost_usd", sa.Float, server_default="0.0"),
        sa.Column("latency_ms", sa.Float, server_default="0.0"),
        sa.Column("status", sa.String(32), server_default="success"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
    )
    op.create_index("ix_usage_records_group_ts", "usage_records", ["group_id", "timestamp"])
    op.create_index("ix_usage_records_agent_ts", "usage_records", ["agent_id", "timestamp"])
    op.create_index("ix_usage_records_model_ts", "usage_records", ["model_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("usage_records")
    op.drop_table("thread_messages")
    op.drop_table("threads")
    op.drop_table("integrations")
    op.drop_table("guardrail_rules")
    op.drop_table("prompt_templates")
    op.drop_table("tools")
    op.drop_table("tenants")
    op.drop_table("users")
