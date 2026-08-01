"""add unique public share codes"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = "0008_video_share_code"
down_revision = "0007_api_token_scopes"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("video", sa.Column("share_code", sa.String(32), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM video WHERE share_code IS NULL")).fetchall()
    for row in rows:
        bind.execute(sa.text("UPDATE video SET share_code=:code WHERE id=:id"), {"code": uuid.uuid4().hex[:16], "id": row[0]})
    op.create_index("ix_video_share_code", "video", ["share_code"], unique=True)

def downgrade():
    op.drop_index("ix_video_share_code", table_name="video")
    op.drop_column("video", "share_code")
