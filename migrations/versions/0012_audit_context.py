"""add moderation audit request context"""
from alembic import op
import sqlalchemy as sa

revision = "0012_audit_context"
down_revision = "0011_media_jobs"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("moderation_audit", sa.Column("ip_address", sa.String(64), nullable=True))
    op.add_column("moderation_audit", sa.Column("user_agent", sa.String(500), nullable=True))
    op.add_column("moderation_audit", sa.Column("video_title", sa.String(140), nullable=True))

def downgrade():
    op.drop_column("moderation_audit", "video_title")
    op.drop_column("moderation_audit", "user_agent")
    op.drop_column("moderation_audit", "ip_address")
