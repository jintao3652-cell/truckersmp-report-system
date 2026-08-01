"""track share views and owner notifications"""
from alembic import op
import sqlalchemy as sa

revision = "0016_share_view_notice"
down_revision = "0015_share_governance"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("share_view_notice", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("video_id", sa.Integer(), sa.ForeignKey("video.id", ondelete="CASCADE"), nullable=False), sa.Column("last_notified_at", sa.DateTime(), nullable=True), sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("video_id", name="uq_share_view_notice_video"))

def downgrade():
    op.drop_table("share_view_notice")
