"""Process pending ffprobe/thumbnail jobs. Run periodically or under a worker supervisor."""
import os
from app import create_app, db
from app.models import MediaJob
from app.utils import make_thumbnail, probe_video, utcnow

app = create_app()
with app.app_context():
    jobs = MediaJob.query.filter_by(status="pending").order_by(MediaJob.created_at).limit(50).all()
    for job in jobs:
        job.status, job.attempts = "running", job.attempts + 1
        db.session.commit()
        try:
            video = job.video
            video.duration = probe_video(video.file_path, app.config["FFPROBE_PATH"]) or 0
            thumb = video.thumbnail_path or os.path.splitext(video.file_path)[0] + ".jpg"
            if make_thumbnail(video.file_path, thumb, app.config["FFMPEG_PATH"]):
                video.thumbnail_path = thumb
            job.status = "completed"
        except Exception as exc:
            job.status = "failed" if job.attempts >= app.config["MEDIA_JOB_MAX_ATTEMPTS"] else "pending"
            job.error = str(exc)[:2000]
            app.logger.exception("Media job %s failed", job.id)
        job.updated_at = utcnow()
        db.session.commit()
