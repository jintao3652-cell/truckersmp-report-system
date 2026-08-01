from datetime import datetime, timedelta, timezone

from flask_login import UserMixin

from . import db, login_manager


def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False, index=True)
    login_failed_count = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    upload_disabled = db.Column(db.Boolean, default=False, nullable=False)
    quota_bytes = db.Column(db.BigInteger)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)

    videos = db.relationship("Video", backref="uploader", lazy=True)
    reset_tokens = db.relationship("PasswordResetToken", backref="user", cascade="all, delete-orphan")
    api_tokens = db.relationship("ApiToken", backref="user", cascade="all, delete-orphan")


class ApiToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    label = db.Column(db.String(80), default="default", nullable=False)
    scopes = db.Column(db.String(255), default="read", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    last_used_at = db.Column(db.DateTime)
    revoked_at = db.Column(db.DateTime)


class UploadSession(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    report_id = db.Column(db.String(64), default="api", nullable=False)
    title = db.Column(db.String(140), default="", nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    expected_size = db.Column(db.BigInteger, nullable=False)
    received_size = db.Column(db.BigInteger, default=0, nullable=False)
    temp_path = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)


class MediaJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = db.Column(db.String(32), nullable=False, default="probe_thumbnail")
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    error = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)
    video = db.relationship("Video", backref=db.backref("media_jobs", cascade="all, delete-orphan"))


class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)


class RateLimitEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(32), nullable=False)
    key_hash = db.Column(db.String(128), nullable=False, index=True)
    window_started_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    blocked_until = db.Column(db.DateTime)
    __table_args__ = (db.UniqueConstraint("action", "key_hash", name="uq_rate_limit_action_key"),)


class LoginAudit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username_input = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    success = db.Column(db.Boolean, nullable=False)
    ip_address = db.Column(db.String(64), nullable=False)
    user_agent = db.Column(db.String(500), default="", nullable=False)
    accept_language = db.Column(db.String(255), default="", nullable=False)
    referrer = db.Column(db.String(500), default="", nullable=False)
    device_type = db.Column(db.String(32), default="unknown", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False, index=True)
    user = db.relationship("User", backref="login_audits")


class ModerationAudit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id", ondelete="SET NULL"), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text, default="", nullable=False)
    source = db.Column(db.String(20), default="web", nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    video_title = db.Column(db.String(140), nullable=True)
    previous_hash = db.Column(db.String(64), nullable=True)
    record_hash = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False, index=True)
    admin = db.relationship("User", foreign_keys=[admin_id])


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(64), index=True, nullable=False)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    thumbnail_path = db.Column(db.String(500), default="", nullable=False)
    file_size = db.Column(db.BigInteger, default=0, nullable=False)
    duration = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    rejection_reason = db.Column(db.Text, default="", nullable=False)
    resubmitted_at = db.Column(db.DateTime)
    uploaded_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    expire_time = db.Column(
        db.DateTime,
        default=lambda: utcnow_naive() + timedelta(days=365),
        nullable=False,
    )
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    share_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    share_enabled = db.Column(db.Boolean, default=True, nullable=False)
    share_expires_at = db.Column(db.DateTime)


class ShareViewNotice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id", ondelete="CASCADE"), nullable=False, unique=True)
    last_notified_at = db.Column(db.DateTime)
    view_count = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)
    video = db.relationship("Video", backref=db.backref("share_view_notice", cascade="all, delete-orphan", uselist=False))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
