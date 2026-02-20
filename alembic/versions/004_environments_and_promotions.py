"""004 – environment_configs and promotion_records tables

Revision ID: 004
Revises: 003
Create Date: 2026-02-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── environment_configs ───────────────────────────────────────
    op.create_table(
        "environment_configs",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("env_id", sa.String(20), nullable=False),
        sa.Column("tenant_id", sa.String(64), server_default="tenant-default"),
        sa.Column("label", sa.String(64), server_default=""),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("variables_json", JSONB, server_default="{}"),
        sa.Column("is_locked", sa.Boolean, server_default="false"),
        sa.Column("locked_by", sa.String(128), server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_env_configs_tenant", "environment_configs", ["tenant_id"])

    # ── promotion_records ─────────────────────────────────────────
    op.create_table(
        "promotion_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), server_default="tenant-default"),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("asset_id", sa.String(64), nullable=False),
        sa.Column("asset_name", sa.String(256), server_default=""),
        sa.Column("from_env", sa.String(20), nullable=False),
        sa.Column("to_env", sa.String(20), nullable=False),
        sa.Column("from_version", sa.Integer, server_default="0"),
        sa.Column("to_version", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("requested_by", sa.String(128), server_default=""),
        sa.Column("approved_by", sa.String(128), server_default=""),
        sa.Column("rejected_by", sa.String(128), server_default=""),
        sa.Column("rejection_reason", sa.Text, server_default=""),
        sa.Column("snapshot_json", JSONB, nullable=True),
        sa.Column("diff_json", JSONB, server_default="{}"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("deployed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_promotions_tenant_env", "promotion_records", ["tenant_id", "to_env"])
    op.create_index("ix_promotions_status", "promotion_records", ["status"])
    op.create_index("ix_promotions_asset", "promotion_records", ["asset_type", "asset_id"])


def downgrade() -> None:
    op.drop_table("promotion_records")
    op.drop_table("environment_configs")
