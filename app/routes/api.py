import hashlib
import os
import secrets
from datetime import timedelta
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request, url_for
from flask_login import current_user, login_required
from .. import db
from ..models import ApiToken, MediaJob, ModerationAudit, UploadSession, User, Video
from ..storage import get_storage
from ..utils import allowed_file, dated_storage_dir, ensure_dir, make_share_code, make_thumbnail, prepare_audit, probe_video, real_video_mime, retention_days, send_notification, send_user_notification, utcnow, valid_report_id

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def token_user():
    value = request.headers.get("Authorization", "")
    if not value.startswith("Bearer "):
        return None
    digest = hashlib.sha256(value[7:].strip().encode()).hexdigest()
    token = ApiToken.query.filter_by(token_hash=digest, revoked_at=None).first()
    if not token:
        return None
    token.last_used_at = utcnow()
    db.session.commit()
    return token.user


def token_scopes():
    value = request.headers.get("Authorization", "")
    if not value.startswith("Bearer "):
        return set()
    digest = hashlib.sha256(value[7:].strip().encode()).hexdigest()
    token = ApiToken.query.filter_by(token_hash=digest, revoked_at=None).first()
    return set((token.scopes or "").split(",")) if token else set()


def has_scope(user, scope):
    if not user:
        return False
    if current_user.is_authenticated:
        effective_admin = user.is_admin or user.role == "admin"
        return (scope == "read") or (effective_admin and scope in {"moderate", "delete"}) or (not effective_admin and user.role == "moderator" and scope == "moderate")
    return scope in token_scopes()


def request_user():
    if current_app.config.get("API_REQUIRE_BEARER") and not request.headers.get("Authorization", "").startswith("Bearer "):
        return None
    return current_user if current_user.is_authenticated else token_user()

@api_bp.get("/videos")
def videos():
    user = request_user()
    if not user:
        return jsonify({"error": "authentication_required"}), 401
    query = Video.query if user.is_admin else Video.query.filter_by(uploader_id=user.id)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 50, type=int), 1), 100)
    pagination = query.order_by(Video.uploaded_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({"items": [{"id": v.id, "title": v.title, "status": v.status, "file_size": v.file_size, "duration": v.duration} for v in pagination.items], "page": pagination.page, "per_page": pagination.per_page, "pages": pagination.pages, "total": pagination.total})


@api_bp.get("/videos/<int:video_id>")
def video_detail(video_id):
    user = request_user()
    if not user:
        return jsonify({"error": "authentication_required"}), 401
    video = Video.query.get_or_404(video_id)
    if not user.is_admin and video.uploader_id != user.id:
        return jsonify({"error": "not_found"}), 404
    media_url = url_for("video.media", video_id=video.id, _external=True)
    share_url = url_for("video.shared_detail", share_code=video.share_code, _external=True) if video.status == "approved" and video.share_enabled else None
    if current_app.config.get("STORAGE_BACKEND") == "s3" and video.status == "approved":
        storage = get_storage(current_app.config)
        if storage.exists(video.file_path):
            media_url = storage.signed_url(video.file_path, current_app.config["STORAGE_SIGNED_URL_SECONDS"])
    return jsonify({"id": video.id, "title": video.title, "description": video.description, "status": video.status, "rejection_reason": video.rejection_reason, "report_id": video.report_id, "file_size": video.file_size, "duration": video.duration, "thumbnail_url": url_for("video.thumbnail", video_id=video.id, _external=True), "media_url": media_url, "share_url": share_url, "uploaded_at": video.uploaded_at.isoformat()})


@api_bp.post("/videos/<int:video_id>/approve")
def approve_video(video_id):
    user = request_user()
    if not user or (not user.is_admin and user.role not in {"admin", "moderator"}) or not has_scope(user, "moderate"):
        return jsonify({"error": "admin_required"}), 403
    video = Video.query.get_or_404(video_id)
    video.status = "approved"
    video.rejection_reason = ""
    db.session.add(prepare_audit(ModerationAudit(video_id=video.id, admin_id=user.id, action="approve", source="api", ip_address=request.remote_addr, user_agent=request.user_agent.string[:500], video_title=video.title)))
    db.session.commit()
    send_user_notification(current_app, video.uploader, "Video approved", f"Video {video.title} was approved via API.")
    return jsonify({"id": video.id, "status": video.status})


@api_bp.post("/videos/<int:video_id>/reject")
def reject_video(video_id):
    user = request_user()
    if not user or (not user.is_admin and user.role not in {"admin", "moderator"}) or not has_scope(user, "moderate"):
        return jsonify({"error": "admin_required"}), 403
    video = Video.query.get_or_404(video_id)
    reason = str((request.get_json(silent=True) or {}).get("reason", "")).strip()[:5000] or "Administrator rejected the video"
    video.status = "rejected"
    video.rejection_reason = reason
    db.session.add(prepare_audit(ModerationAudit(video_id=video.id, admin_id=user.id, action="reject", reason=reason, source="api", ip_address=request.remote_addr, user_agent=request.user_agent.string[:500], video_title=video.title)))
    db.session.commit()
    send_user_notification(current_app, video.uploader, "Video rejected", f"Video {video.title} was rejected. Reason: {reason}")
    return jsonify({"id": video.id, "status": video.status, "rejection_reason": reason})


@api_bp.delete("/videos/<int:video_id>")
def delete_video(video_id):
    user = request_user()
    if not user or (not user.is_admin and user.role != "admin") or not has_scope(user, "delete"):
        return jsonify({"error": "admin_required"}), 403
    video = Video.query.get_or_404(video_id)
    try:
        if current_app.config.get("STORAGE_BACKEND") == "s3":
            storage = get_storage(current_app.config)
            for key in (video.file_path, video.thumbnail_path):
                if key:
                    storage.delete(key)
        else:
            for path in (video.file_path, video.thumbnail_path):
                if path and os.path.exists(path):
                    os.remove(path)
        db.session.add(prepare_audit(ModerationAudit(video_id=video.id, admin_id=user.id, action="delete", reason="Deleted through API", source="api", ip_address=request.remote_addr, user_agent=request.user_agent.string[:500], video_title=video.title)))
        db.session.delete(video)
        db.session.commit()
    except OSError:
        db.session.rollback()
        current_app.logger.exception("API video deletion failed")
        return jsonify({"error": "file_delete_failed"}), 500
    return jsonify({"status": "deleted", "id": video_id})


@api_bp.get("/uploads/<session_id>")
def upload_status(session_id):
    user = request_user()
    session = db.session.query(UploadSession).with_for_update().filter_by(id=session_id).first_or_404()
    if not user or (not user.is_admin and session.user_id != user.id):
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"id": session.id, "status": session.status, "received_size": session.received_size, "expected_size": session.expected_size, "complete": session.received_size == session.expected_size})


@api_bp.post("/uploads")
def init_upload():
    user = request_user()
    if not user:
        return jsonify({"error": "authentication_required"}), 401
    payload = request.get_json(silent=True) or {}
    filename = str(payload.get("filename", "")).strip()
    try:
        size = int(payload.get("size", 0) or 0)
    except (TypeError, ValueError):
        size = 0
    if not filename or not allowed_file(filename) or size <= 0:
        return jsonify({"error": "invalid_filename_or_size"}), 400
    if not valid_report_id(str(payload.get("report_id", "api"))):
        return jsonify({"error": "invalid_report_id"}), 400
    resume_id = str(payload.get("resume_id", "")).strip()
    if resume_id:
        existing = UploadSession.query.filter_by(id=resume_id, user_id=user.id, filename=filename[:255], expected_size=size, status="active").first()
        if existing:
            return jsonify({"id": existing.id, "received_size": existing.received_size, "resumed": True}), 200
    if user.upload_disabled:
        return jsonify({"error": "upload_disabled"}), 403
    usage = db.session.query(db.func.coalesce(db.func.sum(Video.file_size), 0)).filter_by(uploader_id=user.id).scalar()
    quota = user.quota_bytes or current_app.config["MAX_USER_STORAGE_BYTES"]
    if usage + size > quota:
        return jsonify({"error": "quota_exceeded"}), 413
    session_id = secrets.token_urlsafe(24)
    temp_dir = ensure_dir(current_app.config["UPLOAD_FOLDER"])
    temp_path = os.path.join(temp_dir, f"chunk_{session_id}.part")
    Path(temp_path).touch()
    db.session.add(UploadSession(id=session_id, user_id=user.id, filename=filename[:255], report_id=str(payload.get("report_id", "api"))[:64], title=str(payload.get("title", filename))[:140], description=str(payload.get("description", ""))[:5000], expected_size=size, temp_path=temp_path))
    db.session.commit()
    return jsonify({"id": session_id, "received_size": 0}), 201


@api_bp.put("/uploads/<session_id>")
def upload_chunk(session_id):
    user = request_user()
    session = db.session.query(UploadSession).with_for_update().filter_by(id=session_id).first_or_404()
    if session.updated_at + timedelta(seconds=current_app.config["UPLOAD_SESSION_EXPIRES_SECONDS"]) < utcnow():
        session.status = "expired"
        db.session.commit()
        return jsonify({"error": "upload_expired"}), 410
    if not user or (not user.is_admin and session.user_id != user.id):
        return jsonify({"error": "forbidden"}), 403
    if session.status != "active":
        return jsonify({"error": "upload_not_active"}), 409
    chunk = request.get_data()
    if len(chunk) > current_app.config["UPLOAD_CHUNK_MAX_BYTES"]:
        return jsonify({"error": "chunk_too_large", "max_bytes": current_app.config["UPLOAD_CHUNK_MAX_BYTES"]}), 413
    offset = request.args.get("offset", type=int, default=session.received_size)
    if offset != session.received_size or not chunk:
        return jsonify({"error": "invalid_offset", "expected_offset": session.received_size}), 409
    if session.received_size + len(chunk) > session.expected_size:
        return jsonify({"error": "chunk_exceeds_expected_size"}), 413
    with open(session.temp_path, "ab") as target:
        target.write(chunk)
    session.received_size += len(chunk)
    session.updated_at = utcnow()
    db.session.commit()
    return jsonify({"id": session.id, "received_size": session.received_size, "complete": session.received_size == session.expected_size})


@api_bp.post("/uploads/<session_id>/complete")
def complete_upload(session_id):
    user = request_user()
    session = db.session.query(UploadSession).with_for_update().filter_by(id=session_id).first_or_404()
    if session.updated_at + timedelta(seconds=current_app.config["UPLOAD_SESSION_EXPIRES_SECONDS"]) < utcnow():
        session.status = "expired"
        db.session.commit()
        return jsonify({"error": "upload_expired"}), 410
    if not user or (not user.is_admin and session.user_id != user.id):
        return jsonify({"error": "forbidden"}), 403
    if session.received_size != session.expected_size:
        return jsonify({"error": "upload_incomplete", "received_size": session.received_size}), 409
    actual_size = os.path.getsize(session.temp_path)
    if actual_size != session.expected_size:
        return jsonify({"error": "size_mismatch", "actual_size": actual_size}), 400
    if current_app.config.get("REQUIRE_REAL_MIME") and not real_video_mime(session.temp_path):
        session.status = "failed"
        db.session.commit()
        if os.path.exists(session.temp_path):
            os.remove(session.temp_path)
        return jsonify({"error": "invalid_mime"}), 400
    usage = db.session.query(db.func.coalesce(db.func.sum(Video.file_size), 0)).filter_by(uploader_id=session.user_id).scalar()
    owner = db.session.get(User, session.user_id)
    quota = owner.quota_bytes or current_app.config["MAX_USER_STORAGE_BYTES"]
    if usage + actual_size > quota:
        session.status = "failed"
        db.session.commit()
        if os.path.exists(session.temp_path):
            os.remove(session.temp_path)
        return jsonify({"error": "quota_exceeded"}), 413
    try:
        duration = None if current_app.config.get("MEDIA_PROCESSING_ASYNC") else probe_video(session.temp_path, current_app.config["FFPROBE_PATH"])
    except (OSError, ValueError):
        session.status = "failed"
        db.session.commit()
        if os.path.exists(session.temp_path):
            os.remove(session.temp_path)
        return jsonify({"error": "invalid_video"}), 400
    if duration is None and current_app.config["REQUIRE_FFPROBE"] and not current_app.config.get("MEDIA_PROCESSING_ASYNC"):
        session.status = "failed"
        db.session.commit()
        if os.path.exists(session.temp_path):
            os.remove(session.temp_path)
        return jsonify({"error": "ffprobe_required"}), 400
    stored_name = make_storage_name(session.filename)
    final_dir = ensure_dir(dated_storage_dir(current_app.config["VIDEO_FOLDER"], utcnow()))
    final_path = os.path.join(final_dir, stored_name)
    thumbnail_path = os.path.join(final_dir, f"{os.path.splitext(stored_name)[0]}.jpg")
    try:
        os.replace(session.temp_path, final_path)
        if current_app.config.get("MEDIA_PROCESSING_ASYNC"):
            thumbnail_path = ""
        elif not make_thumbnail(final_path, thumbnail_path, current_app.config["FFMPEG_PATH"]):
            thumbnail_path = ""
        file_ref, thumbnail_ref = final_path, thumbnail_path
        if current_app.config.get("STORAGE_BACKEND") == "s3":
            storage = get_storage(current_app.config)
            key = os.path.relpath(final_path, current_app.config["VIDEO_FOLDER"]).replace(os.sep, "/")
            file_ref = storage.put(final_path, key)
            if thumbnail_path and os.path.exists(thumbnail_path):
                thumbnail_ref = storage.put(thumbnail_path, os.path.splitext(key)[0] + ".jpg")
            else:
                thumbnail_ref = ""
        video = Video(report_id=session.report_id, title=session.title or session.filename, description=session.description, original_filename=session.filename, stored_filename=stored_name, file_path=file_ref, thumbnail_path=thumbnail_ref, file_size=actual_size, duration=duration or 0, uploader_id=session.user_id, uploaded_at=utcnow(), expire_time=utcnow() + timedelta(days=retention_days(current_app)), share_code=make_share_code())
        db.session.add(video)
        if current_app.config.get("MEDIA_PROCESSING_ASYNC"):
            db.session.flush()
            db.session.add(MediaJob(video_id=video.id, job_type="probe_thumbnail"))
        session.status = "completed"
        db.session.commit()
    except Exception:
        db.session.rollback()
        for path in (session.temp_path, final_path, thumbnail_path):
            if path and os.path.exists(path):
                os.remove(path)
        current_app.logger.exception("Chunked upload completion failed")
        return jsonify({"error": "completion_failed"}), 500
    send_notification(current_app, "New video awaiting review", f"Video #{video.id} ({video.title}) was uploaded through the API.")
    return jsonify({"id": video.id, "status": video.status}), 201


@api_bp.delete("/uploads/<session_id>")
def cancel_upload(session_id):
    user = request_user()
    session = db.session.query(UploadSession).with_for_update().filter_by(id=session_id).first_or_404()
    if not user or (not user.is_admin and session.user_id != user.id):
        return jsonify({"error": "forbidden"}), 403
    if os.path.exists(session.temp_path):
        os.remove(session.temp_path)
    db.session.delete(session)
    db.session.commit()
    return jsonify({"status": "cancelled"})
