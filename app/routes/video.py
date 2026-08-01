import os
from datetime import timedelta

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from .. import db
from ..forms import UploadForm
from ..models import Video
from ..utils import allowed_file, dated_storage_dir, ensure_dir, format_bytes, make_storage_name, utcnow

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
        file = form.video_file.data
        if not file or not allowed_file(file.filename):
            flash("视频格式不受支持。", "danger")
            return render_template("upload.html", form=form)

        stored_name = make_storage_name(file.filename)
        upload_dir = ensure_dir(current_app.config["UPLOAD_FOLDER"])
        temp_path = os.path.join(upload_dir, stored_name)
        final_path = None
        try:
            file.save(temp_path)
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
                duration=0,
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
    return render_template("video_detail.html", video=video, file_url=url_for("video.media", video_id=video.id))


@video_bp.route("/media/<int:video_id>")
def media(video_id):
    video = Video.query.get_or_404(video_id)
    if not current_user.is_authenticated or (not current_user.is_admin and video.uploader_id != current_user.id):
        abort(404)
    if not os.path.exists(video.file_path):
        abort(404)
    folder = os.path.dirname(video.file_path)
    filename = os.path.basename(video.file_path)
    return send_from_directory(folder, filename, as_attachment=False)
