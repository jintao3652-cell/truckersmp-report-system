from datetime import datetime, timedelta, timezone

from flask_login import UserMixin

from . import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    videos = db.relationship("Video", backref="uploader", lazy=True)
    reset_tokens = db.relationship("PasswordResetToken", backref="user", cascade="all, delete-orphan")


class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class RateLimitEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(32), nullable=False)
    key_hash = db.Column(db.String(128), nullable=False, index=True)
    window_started_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    blocked_until = db.Column(db.DateTime)
    __table_args__ = (db.UniqueConstraint("action", "key_hash", name="uq_rate_limit_action_key"),)


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
    status = db.Column(db.String(20), default="approved", nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expire_time = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=365),
        nullable=False,
    )
    uploader_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
