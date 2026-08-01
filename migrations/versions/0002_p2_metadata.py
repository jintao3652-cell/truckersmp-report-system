"""add moderation metadata

Revision ID: 0002_p2_metadata
Revises: 0001_initial_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_p2_metadata"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("video", sa.Column("rejection_reason", sa.Text(), nullable=False, server_default=""))
    op.create_table(
        "moderation_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("video.id"), nullable=False),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_moderation_audit_created_at", "moderation_audit", ["created_at"])


def downgrade():
    op.drop_index("ix_moderation_audit_created_at", table_name="moderation_audit")
    op.drop_table("moderation_audit")
    op.drop_column("video", "rejection_reason")
