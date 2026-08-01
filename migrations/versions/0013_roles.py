"""add explicit user roles"""
from alembic import op
import sqlalchemy as sa

revision = "0013_roles"
down_revision = "0012_audit_context"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("user", sa.Column("role", sa.String(20), nullable=True, server_default="user"))
    op.execute("UPDATE user SET role='admin' WHERE is_admin=1")
    op.create_index("ix_user_role", "user", ["role"])

def downgrade():
    op.drop_index("ix_user_role", table_name="user")
    op.drop_column("user", "role")
