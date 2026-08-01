"""Process pending ffprobe/thumbnail jobs. Run periodically or under a worker supervisor."""
import os
import tempfile
from app import create_app, db
from app.models import MediaJob
from app.utils import make_thumbnail, probe_video, utcnow
from app.storage import get_storage

app = create_app()
with app.app_context():
    jobs = MediaJob.query.filter_by(status="pending").order_by(MediaJob.created_at).limit(50).all()
    for job in jobs:
        job.status, job.attempts = "running", job.attempts + 1
        db.session.commit()
        try:
            video = job.video
            source_path = video.file_path
            temp_source = None
            storage = get_storage(app.config)
            if app.config.get("STORAGE_BACKEND") == "s3":
                temp_source = tempfile.NamedTemporaryFile(suffix=os.path.splitext(video.original_filename)[1], delete=False).name
                storage.download(video.file_path, temp_source)
                source_path = temp_source
            video.duration = probe_video(source_path, app.config["FFPROBE_PATH"]) or 0
            thumb = os.path.splitext(source_path)[0] + ".jpg"
            if make_thumbnail(source_path, thumb, app.config["FFMPEG_PATH"]):
                if app.config.get("STORAGE_BACKEND") == "s3":
                    key = os.path.splitext(video.file_path)[0] + ".jpg"
                    video.thumbnail_path = storage.upload_key(thumb, key)
                    os.unlink(thumb)
                else:
                    video.thumbnail_path = thumb
            if temp_source and os.path.exists(temp_source):
                os.unlink(temp_source)
            job.status = "completed"
        except Exception as exc:
            job.status = "failed" if job.attempts >= app.config["MEDIA_JOB_MAX_ATTEMPTS"] else "pending"
            job.error = str(exc)[:2000]
            app.logger.exception("Media job %s failed", job.id)
        job.updated_at = utcnow()
        db.session.commit()
