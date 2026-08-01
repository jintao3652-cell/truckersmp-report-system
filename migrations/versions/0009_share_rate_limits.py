"""share rate limiting uses existing rate limit table; no schema changes"""
revision = "0009_share_rate_limits"
down_revision = "0008_video_share_code"
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
