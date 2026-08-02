"""track upload session activity"""
from alembic import op
import sqlalchemy as sa

revision = "0006_upload_session_activity"
down_revision = "0005_upload_sessions"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("upload_session")}
    if "updated_at" not in columns:
        op.add_column("upload_session", sa.Column("updated_at", sa.DateTime(), nullable=True))
    bind.execute(sa.text("UPDATE upload_session SET updated_at = created_at WHERE updated_at IS NULL"))
    if bind.dialect.name != "sqlite":
        op.alter_column("upload_session", "updated_at", existing_type=sa.DateTime(), nullable=False)


def downgrade():
    op.drop_column("upload_session", "updated_at")
