import os
from mimetypes import guess_type
from datetime import timedelta

from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from .. import db
from ..forms import UploadForm
from ..models import MediaJob, Video
from ..storage import get_storage
from ..utils import allowed_file, check_rate_limit, check_user_rate_limit, dated_storage_dir, ensure_dir, format_bytes, make_share_code, make_storage_name, make_thumbnail, notify_share_view, probe_video, real_video_mime, retention_days, send_notification, utcnow, valid_report_id

video_bp = Blueprint("video", __name__)


def _upload_page(form, status=200):
    usage = db.session.query(db.func.coalesce(db.func.sum(Video.file_size), 0)).filter_by(uploader_id=current_user.id).scalar()
    quota = current_user.quota_bytes or current_app.config["MAX_USER_STORAGE_BYTES"]
    return render_template("upload.html", form=form, used_bytes=usage, quota_bytes=quota), status


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
            return _upload_page(form, 429)
        allowed, retry = check_user_rate_limit(current_app, "upload", current_user.id)
        if not allowed:
            flash(f"当前账号上传过于频繁，请 {retry} 秒后再试。", "warning")
            return _upload_page(form, 429)
        file = form.video_file.data
        if not valid_report_id(form.report_id.data):
            flash("举报 ID 格式无效。", "danger")
            return _upload_page(form, 400)
        if not file or not allowed_file(file.filename):
            flash("视频格式不受支持。", "danger")
            return _upload_page(form, 400)
        if current_user.upload_disabled:
            flash("当前账号已被禁止上传。", "danger")
            return _upload_page(form, 403)
        stored_name = make_storage_name(file.filename)
        upload_dir = ensure_dir(current_app.config["UPLOAD_FOLDER"])
        temp_path = os.path.join(upload_dir, stored_name)
        final_path = None
        try:
            file.save(temp_path)
            file_size = os.path.getsize(temp_path)
            if current_app.config.get("REQUIRE_REAL_MIME") and not real_video_mime(temp_path):
                raise ValueError("file type does not match a supported video")
            current_usage = db.session.query(db.func.coalesce(db.func.sum(Video.file_size), 0)).filter_by(uploader_id=current_user.id).scalar()
            quota = current_user.quota_bytes or current_app.config["MAX_USER_STORAGE_BYTES"]
            if current_usage + file_size > quota:
                raise QuotaExceeded
            duration = None if current_app.config.get("MEDIA_PROCESSING_ASYNC") else probe_video(temp_path, current_app.config["FFPROBE_PATH"])
            if duration is None and current_app.config["REQUIRE_FFPROBE"] and not current_app.config.get("MEDIA_PROCESSING_ASYNC"):
                raise ValueError("ffprobe is required for video validation")
            final_dir = ensure_dir(dated_storage_dir(current_app.config["VIDEO_FOLDER"], utcnow()))
            final_path = os.path.join(final_dir, stored_name)
            os.replace(temp_path, final_path)
            thumbnail_path = os.path.join(final_dir, f"{os.path.splitext(stored_name)[0]}.jpg")
            if current_app.config.get("MEDIA_PROCESSING_ASYNC"):
                thumbnail_path = ""
            elif not make_thumbnail(final_path, thumbnail_path, current_app.config["FFMPEG_PATH"]):
                thumbnail_path = ""

            stored_size = os.path.getsize(final_path)
            file_ref, thumbnail_ref = final_path, thumbnail_path
            if current_app.config.get("STORAGE_BACKEND") == "s3":
                storage = get_storage(current_app.config)
                key = os.path.relpath(final_path, current_app.config["VIDEO_FOLDER"]).replace(os.sep, "/")
                file_ref = storage.put(final_path, key)
                if thumbnail_path and os.path.exists(thumbnail_path):
                    thumbnail_ref = storage.put(thumbnail_path, os.path.splitext(key)[0] + ".jpg")
                else:
                    thumbnail_ref = ""
            video = Video(
                report_id=form.report_id.data.strip(),
                title=form.title.data.strip(),
                description=(form.description.data or "").strip(),
                original_filename=file.filename,
                stored_filename=stored_name,
                file_path=file_ref,
                thumbnail_path=thumbnail_ref,
                file_size=stored_size,
                duration=duration or 0,
                uploader_id=current_user.id,
                uploaded_at=utcnow(),
                expire_time=utcnow() + timedelta(days=retention_days(current_app)),
                share_code=make_share_code(),
            )
            db.session.add(video)
            db.session.commit()
            if current_app.config.get("MEDIA_PROCESSING_ASYNC"):
                db.session.flush()
                db.session.add(MediaJob(video_id=video.id, job_type="probe_thumbnail"))
                db.session.commit()
            send_notification(current_app, "新视频等待审核", f"视频 #{video.id}（{video.title}）已上传，等待管理员审核。")
        except QuotaExceeded:
            db.session.rollback()
            if os.path.exists(temp_path):
                os.remove(temp_path)
            flash("已超过个人视频容量配额。", "danger")
            return _upload_page(form, 413)
        except ValueError as exc:
            db.session.rollback()
            for path in (temp_path, final_path):
                if path and os.path.exists(path):
                    os.remove(path)
            flash(f"视频校验失败：{exc}", "danger")
            return _upload_page(form, 400)
        except Exception:
            db.session.rollback()
            for path in (temp_path, final_path):
                if path and os.path.exists(path):
                    os.remove(path)
            current_app.logger.exception("Video upload failed")
            flash("上传失败，请稍后重试。", "danger")
            return _upload_page(form, 500)
        flash("上传成功，等待审核。", "success")
        return redirect(url_for("video.detail", video_id=video.id))
    usage = db.session.query(db.func.coalesce(db.func.sum(Video.file_size), 0)).filter_by(uploader_id=current_user.id).scalar()
    return render_template("upload.html", form=form, used_bytes=usage, quota_bytes=current_user.quota_bytes or current_app.config["MAX_USER_STORAGE_BYTES"])


@video_bp.route("/<int:video_id>")
def detail(video_id):
    video = Video.query.get_or_404(video_id)
    if not current_user.is_authenticated or (not current_user.is_admin and video.uploader_id != current_user.id):
        abort(404)
    mime_type = guess_type(video.original_filename)[0] or "application/octet-stream"
    return render_template("video_detail.html", video=video, file_url=url_for("video.media", video_id=video.id), mime_type=mime_type)


@video_bp.post("/<int:video_id>/resubmit")
@login_required
def resubmit(video_id):
    video = Video.query.get_or_404(video_id)
    if video.uploader_id != current_user.id or video.status != "rejected":
        abort(403)
    video.status = "pending"
    video.resubmitted_at = utcnow()
    db.session.commit()
    flash("视频已重新提交审核。", "success")
    return redirect(url_for("video.detail", video_id=video.id))


@video_bp.route("/share/<share_code>")
def shared_detail(share_code):
    allowed, _ = check_rate_limit(current_app, "share", request.remote_addr)
    if not allowed:
        abort(429)
    video = Video.query.filter_by(share_code=share_code, status="approved", share_enabled=True).first_or_404()
    if video.expire_time < utcnow() or (video.share_expires_at and video.share_expires_at < utcnow()):
        abort(404)
    mime_type = guess_type(video.original_filename)[0] or "application/octet-stream"
    return render_template("video_detail.html", video=video, file_url=url_for("video.shared_media", share_code=share_code), mime_type=mime_type, shared=True)


@video_bp.route("/media/<int:video_id>")
def media(video_id):
    video = Video.query.get_or_404(video_id)
    if not current_user.is_authenticated or (not current_user.is_admin and video.uploader_id != current_user.id):
        abort(404)
    if current_app.config.get("STORAGE_BACKEND") == "s3":
        storage = get_storage(current_app.config)
        if not storage.exists(video.file_path):
            abort(404)
        return redirect(storage.signed_url(video.file_path, current_app.config["STORAGE_SIGNED_URL_SECONDS"]))
    if not os.path.exists(video.file_path):
        abort(404)
    # Nginx can serve the large file directly when configured with X-Accel-Redirect.
    if current_app.config.get("MEDIA_ACCEL_REDIRECT", True):
        base = os.path.realpath(current_app.config["VIDEO_FOLDER"])
        real_path = os.path.realpath(video.file_path)
        if os.path.commonpath((base, real_path)) != base:
            current_app.logger.error("Video path outside VIDEO_FOLDER: %s", video.file_path)
            abort(500)
        relative_path = os.path.relpath(real_path, base).replace(os.sep, "/")
        return Response(status=200, headers={"X-Accel-Redirect": f"/protected-videos/{relative_path}", "Content-Type": guess_type(video.original_filename)[0] or "application/octet-stream", "Content-Disposition": "inline"})
    return send_file(video.file_path, as_attachment=False, conditional=True)


@video_bp.route("/share/<share_code>/media")
def shared_media(share_code):
    allowed, _ = check_rate_limit(current_app, "share", request.remote_addr)
    if not allowed:
        abort(429)
    video = Video.query.filter_by(share_code=share_code, status="approved", share_enabled=True).first_or_404()
    if video.expire_time < utcnow() or (video.share_expires_at and video.share_expires_at < utcnow()):
        abort(404)
    notify_share_view(current_app, video, request.remote_addr)
    if current_app.config.get("STORAGE_BACKEND") == "s3":
        storage = get_storage(current_app.config)
        if not storage.exists(video.file_path):
            abort(404)
        return redirect(storage.signed_url(video.file_path, current_app.config["STORAGE_SIGNED_URL_SECONDS"]))
    if not os.path.exists(video.file_path):
        abort(404)
    if current_app.config.get("MEDIA_ACCEL_REDIRECT", True):
        base = os.path.realpath(current_app.config["VIDEO_FOLDER"])
        real_path = os.path.realpath(video.file_path)
        if os.path.commonpath((base, real_path)) != base:
            abort(500)
        relative_path = os.path.relpath(real_path, base).replace(os.sep, "/")
        return Response(status=200, headers={"X-Accel-Redirect": f"/protected-videos/{relative_path}", "Content-Type": guess_type(video.original_filename)[0] or "application/octet-stream", "Content-Disposition": "inline"})
    return send_file(video.file_path, as_attachment=False, conditional=True)


@video_bp.route("/<int:video_id>/thumbnail")
def thumbnail(video_id):
    video = Video.query.get_or_404(video_id)
    if not current_user.is_authenticated or (not current_user.is_admin and video.uploader_id != current_user.id):
        abort(404)
    if not video.thumbnail_path:
        abort(404)
    if current_app.config.get("STORAGE_BACKEND") == "s3":
        storage = get_storage(current_app.config)
        if not storage.exists(video.thumbnail_path):
            abort(404)
        return redirect(storage.signed_url(video.thumbnail_path, current_app.config["STORAGE_SIGNED_URL_SECONDS"]))
    if not os.path.exists(video.thumbnail_path):
        abort(404)
    return send_file(video.thumbnail_path, mimetype="image/jpeg")


class QuotaExceeded(Exception):
    pass
