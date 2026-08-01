"""add resubmission timestamp"""
from alembic import op
import sqlalchemy as sa

revision = "0010_resubmission"
down_revision = "0009_share_rate_limits"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("video", sa.Column("resubmitted_at", sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column("video", "resubmitted_at")
