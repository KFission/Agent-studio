"""Initial agents and credentials tables

Revision ID: 001
Revises: None
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Provider credentials table
    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("credential_blob", sa.Text, nullable=False),
        sa.Column("display_metadata", JSONB, server_default="{}"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(128), server_default=""),
    )
    op.create_index("ix_provider_credentials_provider", "provider_credentials", ["provider"])

    # Agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("status", sa.String(32), server_default="draft"),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("model_config_json", JSONB, server_default="{}"),
        sa.Column("context", sa.Text, server_default=""),
        sa.Column("prompt_template_id", sa.String(128), nullable=True),
        sa.Column("rag_config_json", JSONB, server_default="{}"),
        sa.Column("memory_config_json", JSONB, server_default="{}"),
        sa.Column("db_config_json", JSONB, server_default="{}"),
        sa.Column("tools_json", JSONB, server_default="[]"),
        sa.Column("endpoint_json", JSONB, server_default="{}"),
        sa.Column("access_control_json", JSONB, server_default="{}"),
        sa.Column("graph_manifest_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(128), server_default=""),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column(
            "credential_id", sa.String(64),
            sa.ForeignKey("provider_credentials.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_agents_name", "agents", ["name"])
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_index("ix_agents_status_updated", "agents", ["status", "updated_at"])
    op.create_index("ix_agents_created_by", "agents", ["created_by"])


def downgrade() -> None:
    op.drop_table("agents")
    op.drop_table("provider_credentials")
