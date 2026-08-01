"""add API token scopes"""
from alembic import op
import sqlalchemy as sa

revision = "0007_api_token_scopes"
down_revision = "0006_upload_session_activity"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("user", sa.Column("quota_bytes", sa.BigInteger(), nullable=True))
    op.add_column("api_token", sa.Column("scopes", sa.String(255), nullable=True, server_default="read"))
    op.execute("UPDATE api_token SET scopes='read' WHERE scopes IS NULL")
    op.add_column("moderation_audit", sa.Column("source", sa.String(20), nullable=True, server_default="web"))

def downgrade():
    op.drop_column("user", "quota_bytes")
    op.drop_column("api_token", "scopes")
    op.drop_column("moderation_audit", "source")
