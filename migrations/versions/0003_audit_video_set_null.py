"""allow moderation audits to survive video deletion"""
from alembic import op
import sqlalchemy as sa

revision = "0003_audit_video_set_null"
down_revision = "0002_p2_metadata"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    foreign_keys = inspector.get_foreign_keys("moderation_audit")
    old_name = next((item.get("name") for item in foreign_keys if item.get("referred_table") == "video"), None)
    with op.batch_alter_table("moderation_audit") as batch:
        batch.alter_column("video_id", existing_type=sa.Integer(), nullable=True)
        if old_name:
            batch.drop_constraint(old_name, type_="foreignkey")
        batch.create_foreign_key("fk_moderation_audit_video", "video", ["video_id"], ["id"], ondelete="SET NULL")

def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    foreign_keys = inspector.get_foreign_keys("moderation_audit")
    old_name = next((item.get("name") for item in foreign_keys if item.get("referred_table") == "video"), None)
    with op.batch_alter_table("moderation_audit") as batch:
        if old_name:
            batch.drop_constraint(old_name, type_="foreignkey")
        batch.create_foreign_key("fk_moderation_audit_video_id", "video", ["video_id"], ["id"])
        batch.alter_column("video_id", existing_type=sa.Integer(), nullable=False)
