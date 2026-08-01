import shutil
from flask import Blueprint, Response, current_app, request
from sqlalchemy import func
from .. import db
from ..models import LoginAudit, Video

metrics_bp = Blueprint("metrics", __name__)

@metrics_bp.get("/metrics")
def metrics():
    if current_app.config.get("METRICS_REQUIRE_AUTH") and request.headers.get("X-Metrics-Token") != current_app.config.get("METRICS_TOKEN"):
        return Response("unauthorized\n", status=401)
    videos = Video.query.count()
    pending = Video.query.filter_by(status="pending").count()
    bytes_used = db.session.query(func.coalesce(func.sum(Video.file_size), 0)).scalar()
    failed_logins = LoginAudit.query.filter_by(success=False).count()
    try:
        usage = shutil.disk_usage(current_app.config["VIDEO_FOLDER"])
    except OSError:
        usage = type("Usage", (), {"used": 0, "total": 0})()
    disk_percent = (usage.used / usage.total * 100) if usage.total else 0
    body = "\n".join(["# TYPE truckersmp_videos_total gauge", f"truckersmp_videos_total {videos}", f"truckersmp_videos_pending {pending}", f"truckersmp_video_bytes_total {bytes_used}", f"truckersmp_login_failures_total {failed_logins}", f"truckersmp_disk_used_percent {disk_percent:.2f}", f"truckersmp_disk_alert {1 if disk_percent >= current_app.config['DISK_ALERT_THRESHOLD'] else 0}"]) + "\n"
    return Response(body, mimetype="text/plain; version=0.0.4")
