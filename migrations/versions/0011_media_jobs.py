"""add asynchronous media processing jobs"""
from alembic import op
import sqlalchemy as sa

revision = "0011_media_jobs"
down_revision = "0010_resubmission"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("media_job", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("video_id", sa.Integer(), sa.ForeignKey("video.id", ondelete="CASCADE"), nullable=False), sa.Column("job_type", sa.String(32), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("error", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_media_job_video_id", "media_job", ["video_id"])
    op.create_index("ix_media_job_status", "media_job", ["status"])

def downgrade():
    op.drop_index("ix_media_job_status", table_name="media_job")
    op.drop_index("ix_media_job_video_id", table_name="media_job")
    op.drop_table("media_job")
