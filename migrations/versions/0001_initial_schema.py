"""initial schema

Revision ID: 0001_initial_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("user", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(64), nullable=False), sa.Column("email", sa.String(120), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("is_admin", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_user_username", "user", ["username"], unique=True)
    op.create_index("ix_user_email", "user", ["email"], unique=True)
    op.create_table("password_reset_token", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("token_hash", sa.String(128), nullable=False), sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=False), sa.Column("used_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_password_reset_token_token_hash", "password_reset_token", ["token_hash"], unique=True)
    op.create_table("rate_limit_event", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("action", sa.String(32), nullable=False), sa.Column("key_hash", sa.String(128), nullable=False), sa.Column("window_started_at", sa.DateTime(), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("blocked_until", sa.DateTime()), sa.UniqueConstraint("action", "key_hash", name="uq_rate_limit_action_key"))
    op.create_index("ix_rate_limit_event_key_hash", "rate_limit_event", ["key_hash"])
    op.create_table("login_audit", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username_input", sa.String(120), nullable=False), sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id")), sa.Column("success", sa.Boolean(), nullable=False), sa.Column("ip_address", sa.String(64), nullable=False), sa.Column("user_agent", sa.String(500), nullable=False), sa.Column("accept_language", sa.String(255), nullable=False), sa.Column("referrer", sa.String(500), nullable=False), sa.Column("device_type", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_login_audit_created_at", "login_audit", ["created_at"])
    op.create_table("video", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("report_id", sa.String(64), nullable=False), sa.Column("title", sa.String(140), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("stored_filename", sa.String(255), nullable=False), sa.Column("file_path", sa.String(500), nullable=False), sa.Column("thumbnail_path", sa.String(500), nullable=False), sa.Column("file_size", sa.BigInteger(), nullable=False), sa.Column("duration", sa.Integer(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("uploaded_at", sa.DateTime(), nullable=False), sa.Column("expire_time", sa.DateTime(), nullable=False), sa.Column("uploader_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False))
    op.create_index("ix_video_report_id", "video", ["report_id"])
    op.create_unique_constraint("uq_video_stored_filename", "video", ["stored_filename"])

def downgrade():
    for table in ("video", "login_audit", "rate_limit_event", "password_reset_token", "user"): op.drop_table(table)
