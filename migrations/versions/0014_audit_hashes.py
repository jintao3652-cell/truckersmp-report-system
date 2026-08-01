"""add tamper-evident moderation audit hashes"""
from alembic import op
import sqlalchemy as sa

revision = "0014_audit_hashes"
down_revision = "0013_roles"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("moderation_audit", sa.Column("previous_hash", sa.String(64), nullable=True))
    op.add_column("moderation_audit", sa.Column("record_hash", sa.String(64), nullable=True))
    op.create_index("ix_moderation_audit_record_hash", "moderation_audit", ["record_hash"])

def downgrade():
    op.drop_index("ix_moderation_audit_record_hash", table_name="moderation_audit")
    op.drop_column("moderation_audit", "record_hash")
    op.drop_column("moderation_audit", "previous_hash")
