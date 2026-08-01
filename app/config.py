import os
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
