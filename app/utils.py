import os
import smtplib
import hashlib
import json
import subprocess
import urllib.request
import re
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename
from . import db
from .models import RateLimitEvent, ShareViewNotice


ALLOWED_EXTENSIONS = {"mp4", "mov", "mkv", "webm", "avi"}
VIDEO_MIME_PREFIXES = {"video/", "application/ogg"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def real_video_mime(path):
    """Inspect magic bytes when python-magic is installed; None means unknown."""
    try:
        import magic
        mime = magic.from_file(path, mime=True)
        return mime if mime.startswith("video/") or mime in VIDEO_MIME_PREFIXES else None
    except (ImportError, OSError):
        return None


def valid_report_id(value):
    """Accept common TruckersMP report identifiers while rejecting arbitrary input."""
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{2,63}", (value or "").strip()))


def audit_hash(previous_hash, audit):
    payload = "|".join(str(value or "") for value in (previous_hash, audit.video_id, audit.admin_id, audit.action, audit.reason, audit.source, audit.ip_address, audit.user_agent, audit.video_title, audit.created_at))
    return hashlib.sha256(payload.encode()).hexdigest()


def prepare_audit(audit):
    from .models import ModerationAudit
    previous = ModerationAudit.query.order_by(ModerationAudit.id.desc()).first()
    audit.previous_hash = previous.record_hash if previous else None
    audit.created_at = utcnow()
    audit.record_hash = audit_hash(audit.previous_hash, audit)
    return audit


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def make_storage_name(original_name: str) -> str:
    stem = secure_filename(original_name) or "video"
    base, ext = os.path.splitext(stem)
    return f"{uuid4().hex}_{base}{ext.lower()}"


def make_share_code():
    return uuid4().hex[:16]


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


def make_thumbnail(video_path, thumbnail_path, ffmpeg_path="ffmpeg"):
    result = subprocess.run([ffmpeg_path, "-y", "-ss", "00:00:01", "-i", video_path, "-frames:v", "1", "-vf", "scale=640:-1", thumbnail_path], capture_output=True, timeout=60, check=False)
    return result.returncode == 0 and os.path.exists(thumbnail_path)


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


def send_notification(app, subject, body):
    """Send optional webhook and email notifications without making them required."""
    delivered = False
    webhook = app.config.get("NOTIFY_WEBHOOK_URL")
    if webhook:
        try:
            payload = json.dumps({"subject": subject, "text": body}).encode()
            req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10):
                delivered = True
        except Exception:
            app.logger.exception("Notification webhook failed")
    recipient = app.config.get("NOTIFY_ADMIN_EMAIL")
    if recipient:
        try:
            delivered = send_email(app, recipient, subject, body) or delivered
        except Exception:
            app.logger.exception("Notification email failed")
    return delivered


def notify_share_view(app, video, viewer_ip=None):
    """Notify the owner once per cooldown window when a public share is viewed."""
    if not video.uploader or not video.uploader.email:
        return False
    now = utcnow()
    notice = ShareViewNotice.query.filter_by(video_id=video.id).first()
    if not notice:
        notice = ShareViewNotice(video_id=video.id, view_count=0)
        db.session.add(notice)
        db.session.flush()
    notice.view_count += 1
    cooldown = app.config.get("SHARE_VIEW_NOTIFY_COOLDOWN_SECONDS", 3600)
    if notice.last_notified_at and (now - notice.last_notified_at).total_seconds() < cooldown:
        db.session.commit()
        return False
    notice.last_notified_at = now
    db.session.commit()
    try:
        return send_email(app, video.uploader.email, "你的视频有人通过分享链接查看", f"你的视频《{video.title}》刚刚被通过分享链接查看。\n分享码：{video.share_code}\n查看时间：{now}。")
    except Exception:
        app.logger.exception("Share view notification failed for video %s", video.id)
        return False


def retention_days(app, category="default"):
    """Resolve RETENTION_POLICY values like 'default:365,reports:90,permanent:0'."""
    raw = str(app.config.get("RETENTION_POLICY", "365"))
    values = {"default": raw}
    if "," in raw:
        values = {part.split(":", 1)[0].strip(): part.split(":", 1)[1].strip() for part in raw.split(",") if ":" in part}
    try:
        value = int(values.get(category, values.get("default", "365")))
        # A zero-day policy means permanent retention, represented by a far-future date.
        return 365000 if value == 0 else (value if value > 0 else 365)
    except ValueError:
        return 365


def check_rate_limit(app, action, ip_address):
    """Return (allowed, retry_after_seconds), storing only a keyed IP hash."""
    now = utcnow()
    digest = hashlib.sha256(f"{app.config['SECRET_KEY']}:{ip_address or 'unknown'}".encode()).hexdigest()
    event = RateLimitEvent.query.filter_by(action=action, key_hash=digest).first()
    prefix = "UPLOAD_RATE_LIMIT_" if action == "upload" else ("SHARE_RATE_LIMIT_" if action == "share" else "RATE_LIMIT_")
    window = app.config[f"{prefix}WINDOW_SECONDS"]
    max_attempts = app.config[f"{prefix}MAX_ATTEMPTS"]
    block_seconds = app.config.get(f"{prefix}BLOCK_SECONDS", app.config["RATE_LIMIT_BLOCK_SECONDS"])
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


def check_user_rate_limit(app, action, user_id):
    return check_rate_limit(app, f"{action}:user", str(user_id))
