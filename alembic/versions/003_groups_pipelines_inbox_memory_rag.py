"""Add groups, pipelines, pipeline_runs, inbox_items, memory_entries,
rag_collections, and rag_documents tables.

Revision ID: 003
Revises: 002
Create Date: 2026-02-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Groups ────────────────────────────────────────────────────
    op.create_table(
        "groups",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False, index=True),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("lob", sa.String(128), server_default="", index=True),
        sa.Column("owner_id", sa.String(128), server_default=""),
        sa.Column("member_ids", JSONB, server_default="[]"),
        sa.Column("allowed_model_ids", JSONB, server_default="[]"),
        sa.Column("allowed_agent_ids", JSONB, server_default="[]"),
        sa.Column("assigned_roles", JSONB, server_default="[]"),
        sa.Column("monthly_budget_usd", sa.Float, server_default="0"),
        sa.Column("daily_token_limit", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── Pipelines ─────────────────────────────────────────────────
    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False, index=True),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("pattern", sa.String(32), server_default="sequential"),
        sa.Column("steps_json", JSONB, server_default="[]"),
        sa.Column("supervisor_agent_id", sa.String(64), nullable=True),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("status", sa.String(32), server_default="draft", index=True),
        sa.Column("owner_id", sa.String(128), server_default=""),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── Pipeline Runs ─────────────────────────────────────────────
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("pipeline_id", sa.String(64), nullable=False, index=True),
        sa.Column("pipeline_name", sa.String(256), server_default=""),
        sa.Column("status", sa.String(32), server_default="running", index=True),
        sa.Column("pattern", sa.String(32), server_default=""),
        sa.Column("steps_completed", sa.Integer, server_default="0"),
        sa.Column("steps_total", sa.Integer, server_default="0"),
        sa.Column("step_results_json", JSONB, server_default="[]"),
        sa.Column("input_data_json", JSONB, server_default="{}"),
        sa.Column("output_data_json", JSONB, server_default="{}"),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("total_latency_ms", sa.Float, server_default="0"),
        sa.Column("total_cost", sa.Float, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_pipeline_runs_pipeline_started", "pipeline_runs", ["pipeline_id", "started_at"])

    # ── Inbox Items ───────────────────────────────────────────────
    op.create_table(
        "inbox_items",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("thread_id", sa.String(64), server_default="", index=True),
        sa.Column("agent_id", sa.String(64), server_default="", index=True),
        sa.Column("tenant_id", sa.String(64), server_default="tenant-default", index=True),
        sa.Column("user_id", sa.String(64), server_default=""),
        sa.Column("status", sa.String(32), server_default="pending", index=True),
        sa.Column("interrupt_json", JSONB, server_default="{}"),
        sa.Column("thread_title", sa.String(512), server_default=""),
        sa.Column("message_count", sa.Integer, server_default="0"),
        sa.Column("last_message_preview", sa.Text, server_default=""),
        sa.Column("action", sa.String(32), nullable=True),
        sa.Column("response_json", JSONB, nullable=True),
        sa.Column("resolved_by", sa.String(128), server_default=""),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("priority", sa.Integer, server_default="0"),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_inbox_items_tenant_status", "inbox_items", ["tenant_id", "status"])
    op.create_index("ix_inbox_items_agent_status", "inbox_items", ["agent_id", "status"])

    # ── Memory Entries ────────────────────────────────────────────
    op.create_table(
        "memory_entries",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("memory_type", sa.String(32), nullable=False, index=True),
        sa.Column("agent_id", sa.String(64), nullable=False, index=True),
        sa.Column("session_id", sa.String(128), server_default="default", index=True),
        sa.Column("role", sa.String(32), server_default="user"),
        sa.Column("content", sa.Text, server_default=""),
        sa.Column("token_count", sa.Integer, server_default="0"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_memory_entries_agent_session", "memory_entries", ["agent_id", "session_id"])
    op.create_index("ix_memory_entries_agent_type", "memory_entries", ["agent_id", "memory_type"])

    # ── RAG Collections ───────────────────────────────────────────
    op.create_table(
        "rag_collections",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False, index=True),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("agent_id", sa.String(64), nullable=True, index=True),
        sa.Column("embedding_model", sa.String(128), server_default="text-embedding-004"),
        sa.Column("document_count", sa.Integer, server_default="0"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── RAG Documents ─────────────────────────────────────────────
    op.create_table(
        "rag_documents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("collection_id", sa.String(64), sa.ForeignKey("rag_collections.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("content", sa.Text, server_default=""),
        sa.Column("content_hash", sa.String(64), server_default=""),
        sa.Column("token_count", sa.Integer, server_default="0"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("rag_documents")
    op.drop_table("rag_collections")
    op.drop_table("memory_entries")
    op.drop_table("inbox_items")
    op.drop_table("pipeline_runs")
    op.drop_table("pipelines")
    op.drop_table("groups")
