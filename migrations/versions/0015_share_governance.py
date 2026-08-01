"""add share enable and expiry controls"""
from alembic import op
import sqlalchemy as sa
revision = "0015_share_governance"
down_revision = "0014_audit_hashes"
branch_labels = None
depends_on = None
def upgrade():
    op.add_column("video", sa.Column("share_enabled", sa.Boolean(), nullable=True, server_default=sa.true()))
    op.add_column("video", sa.Column("share_expires_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE video SET share_enabled=1 WHERE share_enabled IS NULL")
def downgrade():
    op.drop_column("video", "share_expires_at")
    op.drop_column("video", "share_enabled")
