"""Add threads, thread_messages, and usage_records tables

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
    # Threads table
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
    op.create_index("ix_threads_agent_id", "threads", ["agent_id"])
    op.create_index("ix_threads_tenant_id", "threads", ["tenant_id"])
    op.create_index("ix_threads_status", "threads", ["status"])
    op.create_index("ix_threads_agent_tenant", "threads", ["agent_id", "tenant_id"])
    op.create_index("ix_threads_user", "threads", ["user_id"])

    # Thread messages table
    op.create_table(
        "thread_messages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "thread_id", sa.String(64),
            sa.ForeignKey("threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False, server_default="user"),
        sa.Column("content", sa.Text, server_default=""),
        sa.Column("tool_calls_json", JSONB, server_default="[]"),
        sa.Column("tool_call_id", sa.String(128), server_default=""),
        sa.Column("name", sa.String(128), server_default=""),
        sa.Column("model", sa.String(128), server_default=""),
        sa.Column("tokens", sa.Integer, server_default="0"),
        sa.Column("latency_ms", sa.Float, server_default="0"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_thread_messages_thread_id", "thread_messages", ["thread_id"])
    op.create_index("ix_thread_messages_thread_created", "thread_messages", ["thread_id", "created_at"])

    # Usage records table
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
        sa.Column("cost_usd", sa.Float, server_default="0"),
        sa.Column("latency_ms", sa.Float, server_default="0"),
        sa.Column("status", sa.String(32), server_default="success"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
    )
    op.create_index("ix_usage_records_timestamp", "usage_records", ["timestamp"])
    op.create_index("ix_usage_records_group_id", "usage_records", ["group_id"])
    op.create_index("ix_usage_records_agent_id", "usage_records", ["agent_id"])
    op.create_index("ix_usage_records_model_id", "usage_records", ["model_id"])
    op.create_index("ix_usage_records_group_ts", "usage_records", ["group_id", "timestamp"])
    op.create_index("ix_usage_records_agent_ts", "usage_records", ["agent_id", "timestamp"])
    op.create_index("ix_usage_records_model_ts", "usage_records", ["model_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("thread_messages")
    op.drop_table("threads")
    op.drop_table("usage_records")
