"""add API tokens"""
from alembic import op
import sqlalchemy as sa

revision = "0004_api_tokens"
down_revision = "0003_audit_video_set_null"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("api_token", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("token_hash", sa.String(128), nullable=False), sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False), sa.Column("label", sa.String(80), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("last_used_at", sa.DateTime()), sa.Column("revoked_at", sa.DateTime()))
    op.create_index("ix_api_token_token_hash", "api_token", ["token_hash"], unique=True)

def downgrade():
    op.drop_index("ix_api_token_token_hash", table_name="api_token")
    op.drop_table("api_token")
