"""add resumable upload sessions"""
from alembic import op
import sqlalchemy as sa

revision = "0005_upload_sessions"
down_revision = "0004_api_tokens"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("upload_session", sa.Column("id", sa.String(64), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("report_id", sa.String(64), nullable=False), sa.Column("title", sa.String(140), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("expected_size", sa.BigInteger(), nullable=False), sa.Column("received_size", sa.BigInteger(), nullable=False), sa.Column("temp_path", sa.String(500), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))

def downgrade():
    op.drop_table("upload_session")
