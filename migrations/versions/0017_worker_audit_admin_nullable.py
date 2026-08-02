"""allow system worker moderation audits without a user admin"""
from alembic import op
import sqlalchemy as sa

revision = "0017_worker_audit_admin_nullable"
down_revision = "0016_share_view_notice"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("moderation_audit") as batch:
        batch.alter_column("admin_id", existing_type=sa.Integer(), nullable=True)

def downgrade():
    with op.batch_alter_table("moderation_audit") as batch:
        batch.alter_column("admin_id", existing_type=sa.Integer(), nullable=False)
