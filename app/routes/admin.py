import os
import csv
import io

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .. import db
from ..models import ApiToken, LoginAudit, ModerationAudit, User, Video
from ..storage import get_storage
from ..utils import send_notification
from ..utils import audit_hash, make_share_code, utcnow

admin_bp = Blueprint("admin", __name__)


def audit_context(video, action, reason=""):
    previous = ModerationAudit.query.order_by(ModerationAudit.id.desc()).first()
    audit = ModerationAudit(video_id=video.id, admin_id=current_user.id, action=action, reason=reason, ip_address=request.remote_addr, user_agent=request.user_agent.string[:500], video_title=video.title, previous_hash=previous.record_hash if previous else None, created_at=utcnow())
    audit.record_hash = audit_hash(audit.previous_hash, audit)
    return audit


@admin_bp.before_request
def guard_admin():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if not current_user.is_admin and current_user.role not in {"admin", "moderator"}:
        flash("需要管理员权限。", "danger")
        return redirect(url_for("main.index"))


@admin_bp.route("/")
def dashboard():
    status = request.args.get("status", "")
    query = Video.query.order_by(Video.uploaded_at.desc())
    if status in {"pending", "approved", "rejected"}:
        query = query.filter_by(status=status)
    page = max(request.args.get("page", 1, type=int), 1)
    pagination = query.paginate(page=page, per_page=25, error_out=False)
    logins = LoginAudit.query.order_by(LoginAudit.created_at.desc()).limit(200).all()
    users = User.query.order_by(User.created_at.desc()).limit(200).all()
    pending_count = Video.query.filter_by(status="pending").count()
    return render_template("admin_dashboard.html", videos=pagination.items, pagination=pagination, logins=logins, users=users, pending_count=pending_count)


@admin_bp.get("/moderation-history")
def moderation_history():
    return render_template("moderation_history.html", audits=ModerationAudit.query.order_by(ModerationAudit.created_at.desc()).limit(500).all())


@admin_bp.get("/users")
def users_page():
    search = request.args.get("q", "").strip()
    query = User.query.order_by(User.created_at.desc())
    if search:
        query = query.filter(db.or_(User.username.contains(search), User.email.contains(search)))
    users = query.paginate(page=max(request.args.get("page", 1, type=int), 1), per_page=25, error_out=False)
    return render_template("admin_users.html", users=users.items, pagination=users, tokens=ApiToken.query.filter_by(revoked_at=None).order_by(ApiToken.created_at.desc()).all())


@admin_bp.post("/users/<int:user_id>/tokens")
def create_token(user_id):
    import hashlib, secrets
    user = User.query.get_or_404(user_id)
    raw = secrets.token_urlsafe(32)
    scopes = {"read"}
    if request.form.get("scope_moderate"):
        scopes.add("moderate")
    if request.form.get("scope_delete"):
        scopes.add("delete")
    db.session.add(ApiToken(token_hash=hashlib.sha256(raw.encode()).hexdigest(), user_id=user.id, label=request.form.get("label", "default")[:80], scopes=",".join(sorted(scopes)) or "read"))
    db.session.commit()
    flash(f"API Token（仅显示一次）：{raw}", "warning")
    return redirect(url_for("admin.users_page"))


@admin_bp.post("/users/<int:user_id>/quota")
def update_quota(user_id):
    user = User.query.get_or_404(user_id)
    raw = request.form.get("quota_bytes", "").strip()
    try:
        value = int(raw) if raw else None
        if value is not None and value < 0:
            raise ValueError
    except ValueError:
        flash("配额必须是非负整数。", "danger")
        return redirect(url_for("admin.users_page"))
    user.quota_bytes = value
    db.session.commit()
    flash("用户配额已更新。", "success")
    return redirect(url_for("admin.users_page"))


@admin_bp.post("/videos/<int:video_id>/regenerate-share")
def regenerate_share(video_id):
    video = Video.query.get_or_404(video_id)
    old_code = video.share_code
    video.share_code = make_share_code()
    audit = audit_context(video, "share_reset", f"Share code rotated from {old_code}")
    db.session.add(audit)
    db.session.commit()
    flash("分享码已重新生成，旧链接已失效。", "success")
    return redirect(url_for("admin.dashboard", status=request.args.get("status", "")))


@admin_bp.post("/tokens/<int:token_id>/revoke")
def revoke_token(token_id):
    token = ApiToken.query.get_or_404(token_id)
    token.revoked_at = utcnow()
    db.session.commit()
    flash("API Token 已撤销。", "success")
    return redirect(url_for("admin.users_page"))


@admin_bp.get("/audit.csv")
def audit_csv():
    from flask import Response
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "type", "username", "action", "success", "ip", "video_id", "admin_id", "details", "previous_hash", "record_hash"])
    for item in LoginAudit.query.order_by(LoginAudit.created_at.desc()).limit(5000):
        writer.writerow([item.created_at, "login", item.username_input, "", item.success, item.ip_address, "", item.user_id, item.user_agent, "", ""])
    for item in ModerationAudit.query.order_by(ModerationAudit.created_at.desc()).limit(5000):
        admin = db.session.get(User, item.admin_id)
        writer.writerow([item.created_at, "moderation", admin.username if admin else "", item.action, "", item.ip_address or "", item.video_id or "", item.admin_id, f"[{item.source}] {item.reason}", item.previous_hash or "", item.record_hash or ""])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=audit.csv"})


@admin_bp.post("/users/<int:user_id>/toggle-upload")
def toggle_upload(user_id):
    user = User.query.get_or_404(user_id)
    user.upload_disabled = not user.upload_disabled
    db.session.commit()
    flash("用户上传权限已更新。", "success")
    return redirect(url_for("admin.users_page", q=request.args.get("q", ""), page=request.args.get("page", 1)))


@admin_bp.post("/users/<int:user_id>/unlock")
def unlock_user(user_id):
    user = User.query.get_or_404(user_id)
    user.locked_until = None
    user.login_failed_count = 0
    db.session.commit()
    flash("账号已解锁。", "success")
    return redirect(url_for("admin.users_page", q=request.args.get("q", ""), page=request.args.get("page", 1)))


@admin_bp.post("/delete/<int:video_id>")
def delete(video_id):
    video = Video.query.get_or_404(video_id)
    file_errors = []
    if current_app.config.get("STORAGE_BACKEND") == "s3":
        storage = get_storage(current_app.config)
        for key in (video.file_path, video.thumbnail_path):
            if key:
                try:
                    storage.delete(key)
                except Exception:
                    current_app.logger.exception("Failed to remove object %s", key)
                    file_errors.append(key)
    else:
        for path in (video.file_path, video.thumbnail_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    current_app.logger.exception("Failed to remove video file %s", path)
                    file_errors.append(path)
    db.session.add(audit_context(video, "delete", "Deleted by administrator"))
    db.session.delete(video)
    db.session.commit()
    flash("记录已删除，但部分文件删除失败，请检查日志。" if file_errors else "视频及其文件已删除。", "warning" if file_errors else "success")
    return redirect(url_for("admin.dashboard", status=request.args.get("status", "")))


@admin_bp.post("/approve/<int:video_id>")
def approve(video_id):
    video = Video.query.get_or_404(video_id)
    video.status = "approved"
    video.rejection_reason = ""
    db.session.add(audit_context(video, "approve"))
    db.session.commit()
    send_notification(current_app, "视频审核通过", f"视频 #{video.id} 已通过审核。")
    flash("已通过。", "success")
    return redirect(url_for("admin.dashboard", status=request.args.get("status", "")))


@admin_bp.post("/reject/<int:video_id>")
def reject(video_id):
    video = Video.query.get_or_404(video_id)
    video.status = "rejected"
    video.rejection_reason = request.form.get("reason", "").strip()[:5000] or "管理员审核拒绝"
    db.session.add(audit_context(video, "reject", video.rejection_reason))
    db.session.commit()
    send_notification(current_app, "视频审核被拒绝", f"视频 #{video.id} 被拒绝：{video.rejection_reason}")
    flash("已拒绝。", "warning")
    return redirect(url_for("admin.dashboard", status=request.args.get("status", "")))
