import os
import shutil
from datetime import timedelta
from pathlib import Path


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    ENVIRONMENT = os.getenv("FLASK_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'truckersmp.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    VIDEO_FOLDER = os.getenv("VIDEO_FOLDER", "/sdk/truckersmp-videos")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 2 * 1024 * 1024 * 1024))
    MAX_USER_STORAGE_BYTES = int(os.getenv("MAX_USER_STORAGE_BYTES", 20 * 1024 * 1024 * 1024))
    FFPROBE_PATH = os.getenv("FFPROBE_PATH", shutil.which("ffprobe") or "")
    FFMPEG_PATH = os.getenv("FFMPEG_PATH", shutil.which("ffmpeg") or "ffmpeg")
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    STORAGE_S3_BUCKET = os.getenv("STORAGE_S3_BUCKET", "")
    STORAGE_S3_ENDPOINT = os.getenv("STORAGE_S3_ENDPOINT", "")
    STORAGE_S3_REGION = os.getenv("STORAGE_S3_REGION", "")
    STORAGE_S3_PREFIX = os.getenv("STORAGE_S3_PREFIX", "videos")
    STORAGE_S3_PUBLIC_BASE = os.getenv("STORAGE_S3_PUBLIC_BASE", "")
    STORAGE_SIGNED_URL_SECONDS = int(os.getenv("STORAGE_SIGNED_URL_SECONDS", "900"))
    REQUIRE_REAL_MIME = os.getenv("REQUIRE_REAL_MIME", "0") == "1"
    MEDIA_PROCESSING_ASYNC = os.getenv("MEDIA_PROCESSING_ASYNC", "0") == "1"
    MEDIA_JOB_MAX_ATTEMPTS = int(os.getenv("MEDIA_JOB_MAX_ATTEMPTS", "3"))
    RETENTION_POLICY = os.getenv("RETENTION_POLICY", "365")
    DISK_ALERT_THRESHOLD = int(os.getenv("DISK_ALERT_THRESHOLD", "90"))
    NOTIFY_WEBHOOK_URL = os.getenv("NOTIFY_WEBHOOK_URL", "")
    NOTIFY_ADMIN_EMAIL = os.getenv("NOTIFY_ADMIN_EMAIL", "")
    API_REQUIRE_BEARER = os.getenv("API_REQUIRE_BEARER", "1" if ENVIRONMENT == "production" else "0") == "1"
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")
    UPLOAD_SESSION_EXPIRES_SECONDS = int(os.getenv("UPLOAD_SESSION_EXPIRES_SECONDS", "86400"))
    UPLOAD_CHUNK_MAX_BYTES = int(os.getenv("UPLOAD_CHUNK_MAX_BYTES", str(16 * 1024 * 1024)))
    SHARE_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("SHARE_RATE_LIMIT_MAX_ATTEMPTS", "120"))
    SHARE_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("SHARE_RATE_LIMIT_WINDOW_SECONDS", "3600"))
    SHARE_RATE_LIMIT_BLOCK_SECONDS = int(os.getenv("SHARE_RATE_LIMIT_BLOCK_SECONDS", "3600"))
    METRICS_REQUIRE_AUTH = os.getenv("METRICS_REQUIRE_AUTH", "1" if ENVIRONMENT == "production" else "0") == "1"
    METRICS_TOKEN = os.getenv("METRICS_TOKEN", "")
    REQUIRE_FFPROBE = os.getenv("REQUIRE_FFPROBE", "1" if ENVIRONMENT == "production" else "0") == "1"
    MEDIA_ACCEL_REDIRECT = os.getenv("MEDIA_ACCEL_REDIRECT", "1") == "1"
    AUTO_CREATE_DB = os.getenv("AUTO_CREATE_DB", "0" if ENVIRONMENT == "production" else "1") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "1") == "1"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "")
    MAIL_PROVIDER = os.getenv("MAIL_PROVIDER", "custom").lower()
    MAIL_RESET_EXPIRES_MINUTES = int(os.getenv("MAIL_RESET_EXPIRES_MINUTES", "30"))
    MAIL_PRESETS = {"gmail": ("smtp.gmail.com", 587, True), "outlook": ("smtp.office365.com", 587, True), "qq": ("smtp.qq.com", 587, True), "163": ("smtp.163.com", 465, False), "aliyun": ("smtp.aliyun.com", 465, False), "custom": (MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS)}
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "900"))
    RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("RATE_LIMIT_MAX_ATTEMPTS", "10"))
    RATE_LIMIT_BLOCK_SECONDS = int(os.getenv("RATE_LIMIT_BLOCK_SECONDS", "900"))
    UPLOAD_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("UPLOAD_RATE_LIMIT_WINDOW_SECONDS", "3600"))
    UPLOAD_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("UPLOAD_RATE_LIMIT_MAX_ATTEMPTS", "10"))
    UPLOAD_RATE_LIMIT_BLOCK_SECONDS = int(os.getenv("UPLOAD_RATE_LIMIT_BLOCK_SECONDS", "3600"))
    MAX_LOGIN_FAILURES = int(os.getenv("MAX_LOGIN_FAILURES", "8"))
    LOGIN_LOCK_SECONDS = int(os.getenv("LOGIN_LOCK_SECONDS", "900"))
