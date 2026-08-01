import os
import smtplib
import hashlib
import json
import subprocess
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename
from . import db
from .models import RateLimitEvent


ALLOWED_EXTENSIONS = {"mp4", "mov", "mkv", "webm", "avi"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def make_storage_name(original_name: str) -> str:
    stem = secure_filename(original_name) or "video"
    base, ext = os.path.splitext(stem)
    return f"{uuid4().hex}_{base}{ext.lower()}"


def dated_storage_dir(base_dir, when=None):
    when = when or utcnow()
    return os.path.join(base_dir, when.strftime("%Y"), when.strftime("%m"), when.strftime("%d"))


def format_bytes(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def probe_video(path, ffprobe_path):
    if not ffprobe_path:
        return None
    result = subprocess.run(
        [ffprobe_path, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type,duration", "-of", "json", path],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if result.returncode != 0:
        raise ValueError("file is not a valid video")
    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    if not streams or streams[0].get("codec_type") != "video":
        raise ValueError("file contains no video stream")
    return int(float(streams[0].get("duration") or 0))


def send_email(app, recipient, subject, body):
    host, port, use_tls = app.config["MAIL_PRESETS"].get(app.config["MAIL_PROVIDER"], app.config["MAIL_PRESETS"]["custom"])
    if not host or not app.config["MAIL_USERNAME"] or not app.config["MAIL_PASSWORD"]:
        app.logger.warning("Email not sent: SMTP is not configured")
        return False
    message = EmailMessage()
    message["Subject"], message["From"], message["To"] = subject, app.config["MAIL_DEFAULT_SENDER"] or app.config["MAIL_USERNAME"], recipient
    message.set_content(body)
    with smtplib.SMTP(host, port, timeout=15) if use_tls else smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls()
        smtp.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
        smtp.send_message(message)
    return True


def check_rate_limit(app, action, ip_address):
    """Return (allowed, retry_after_seconds), storing only a keyed IP hash."""
    now = utcnow()
    digest = hashlib.sha256(f"{app.config['SECRET_KEY']}:{ip_address or 'unknown'}".encode()).hexdigest()
    event = RateLimitEvent.query.filter_by(action=action, key_hash=digest).first()
    prefix = "UPLOAD_RATE_LIMIT_" if action == "upload" else "RATE_LIMIT_"
    window = app.config[f"{prefix}WINDOW_SECONDS"]
    max_attempts = app.config[f"{prefix}MAX_ATTEMPTS"]
    block_seconds = app.config[f"{prefix}BLOCK_SECONDS"]
    if not event or (now - event.window_started_at).total_seconds() >= window:
        if not event:
            event = RateLimitEvent(action=action, key_hash=digest, window_started_at=now, attempts=0)
            db.session.add(event)
        else:
            event.window_started_at, event.attempts, event.blocked_until = now, 0, None
    if event.blocked_until and event.blocked_until > now:
        db.session.commit()
        return False, max(1, int((event.blocked_until - now).total_seconds()))
    event.attempts += 1
    if event.attempts > max_attempts:
        event.blocked_until = now + timedelta(seconds=block_seconds)
        db.session.commit()
        return False, block_seconds
    db.session.commit()
    return True, 0
