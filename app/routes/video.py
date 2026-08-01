import os
from mimetypes import guess_type
from datetime import timedelta

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from .. import db
from ..forms import UploadForm
from ..models import Video
from ..utils import allowed_file, check_rate_limit, dated_storage_dir, ensure_dir, format_bytes, make_storage_name, probe_video, utcnow

video_bp = Blueprint("video", __name__)


@video_bp.route("/")
@login_required
def list_videos():
    query = Video.query
    if not current_user.is_admin:
        query = query.filter(Video.uploader_id == current_user.id)
    query = query.order_by(Video.uploaded_at.desc())
    report_id = request.args.get("report_id", "").strip()
    title = request.args.get("title", "").strip()
    if report_id:
        query = query.filter(Video.report_id.contains(report_id))
    if title:
        query = query.filter(Video.title.contains(title))
    page = max(request.args.get("page", 1, type=int), 1)
    pagination = query.paginate(page=page, per_page=20, error_out=False)
    return render_template("video_list.html", videos=pagination.items, pagination=pagination, format_bytes=format_bytes)


@video_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    form = UploadForm()
    if form.validate_on_submit():
        allowed, retry = check_rate_limit(current_app, "upload", request.remote_addr)
        if not allowed:
            flash(f"上传过于频繁，请 {retry} 秒后再试。", "warning")
            return render_template("upload.html", form=form), 429
        file = form.video_file.data
        if not file or not allowed_file(file.filename):
            flash("视频格式不受支持。", "danger")
            return render_template("upload.html", form=form)
        current_usage = db.session.query(db.func.coalesce(db.func.sum(Video.file_size), 0)).filter_by(uploader_id=current_user.id).scalar()
        if current_usage + (request.content_length or 0) > current_app.config["MAX_USER_STORAGE_BYTES"]:
            flash("已超过个人视频容量配额。", "danger")
            return render_template("upload.html", form=form), 413

        stored_name = make_storage_name(file.filename)
        upload_dir = ensure_dir(current_app.config["UPLOAD_FOLDER"])
        temp_path = os.path.join(upload_dir, stored_name)
        final_path = None
        try:
            file.save(temp_path)
            duration = probe_video(temp_path, current_app.config["FFPROBE_PATH"])
            if duration is None and current_app.config["REQUIRE_FFPROBE"]:
                raise ValueError("ffprobe is required for video validation")
            final_dir = ensure_dir(dated_storage_dir(current_app.config["VIDEO_FOLDER"], utcnow()))
            final_path = os.path.join(final_dir, stored_name)
            os.replace(temp_path, final_path)

            video = Video(
                report_id=form.report_id.data.strip(),
                title=form.title.data.strip(),
                description=(form.description.data or "").strip(),
                original_filename=file.filename,
                stored_filename=stored_name,
                file_path=final_path,
                file_size=os.path.getsize(final_path),
                duration=duration or 0,
                uploader_id=current_user.id,
                uploaded_at=utcnow(),
                expire_time=utcnow() + timedelta(days=365),
            )
            db.session.add(video)
            db.session.commit()
        except Exception:
            db.session.rollback()
            for path in (temp_path, final_path):
                if path and os.path.exists(path):
                    os.remove(path)
            current_app.logger.exception("Video upload failed")
            flash("上传失败，请稍后重试。", "danger")
            return render_template("upload.html", form=form), 500
        flash("上传成功，等待审核。", "success")
        return redirect(url_for("video.detail", video_id=video.id))
    return render_template("upload.html", form=form)


@video_bp.route("/<int:video_id>")
def detail(video_id):
    video = Video.query.get_or_404(video_id)
    if not current_user.is_authenticated or (not current_user.is_admin and video.uploader_id != current_user.id):
        abort(404)
    mime_type = guess_type(video.original_filename)[0] or "application/octet-stream"
    return render_template("video_detail.html", video=video, file_url=url_for("video.media", video_id=video.id), mime_type=mime_type)


@video_bp.route("/media/<int:video_id>")
def media(video_id):
    video = Video.query.get_or_404(video_id)
    if not current_user.is_authenticated or (not current_user.is_admin and video.uploader_id != current_user.id):
        abort(404)
    if not os.path.exists(video.file_path):
        abort(404)
    response = send_file(video.file_path, as_attachment=False, conditional=True)
    # Nginx can serve the large file directly when configured with X-Accel-Redirect.
    if current_app.config.get("MEDIA_ACCEL_REDIRECT", True):
        relative_path = os.path.relpath(video.file_path, current_app.config["VIDEO_FOLDER"]).replace(os.sep, "/")
        response.headers["X-Accel-Redirect"] = f"/protected-videos/{relative_path}"
        response.headers["Content-Disposition"] = "inline"
        response.direct_passthrough = True
    return response
