"""allow moderation audits to survive video deletion"""
from alembic import op

revision = "0003_audit_video_set_null"
down_revision = "0002_p2_metadata"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("moderation_audit") as batch:
        batch.alter_column("video_id", nullable=True)
        batch.drop_constraint(None, type_="foreignkey")
        batch.create_foreign_key("fk_moderation_audit_video", "video", ["video_id"], ["id"], ondelete="SET NULL")

def downgrade():
    pass
