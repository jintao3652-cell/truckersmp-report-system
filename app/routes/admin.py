import os

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .. import db
from ..models import LoginAudit, ModerationAudit, Video

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
def guard_admin():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if not current_user.is_admin:
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
    return render_template("admin_dashboard.html", videos=pagination.items, pagination=pagination, logins=logins)


@admin_bp.post("/delete/<int:video_id>")
def delete(video_id):
    video = Video.query.get_or_404(video_id)
    file_errors = []
    for path in (video.file_path, video.thumbnail_path):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                current_app.logger.exception("Failed to remove video file %s", path)
                file_errors.append(path)
    db.session.delete(video)
    db.session.commit()
    flash("记录已删除，但部分文件删除失败，请检查日志。" if file_errors else "视频及其文件已删除。", "warning" if file_errors else "success")
    return redirect(url_for("admin.dashboard", status=request.args.get("status", "")))


@admin_bp.post("/approve/<int:video_id>")
def approve(video_id):
    video = Video.query.get_or_404(video_id)
    video.status = "approved"
    video.rejection_reason = ""
    db.session.add(ModerationAudit(video_id=video.id, admin_id=current_user.id, action="approve"))
    db.session.commit()
    flash("已通过。", "success")
    return redirect(url_for("admin.dashboard", status=request.args.get("status", "")))


@admin_bp.post("/reject/<int:video_id>")
def reject(video_id):
    video = Video.query.get_or_404(video_id)
    video.status = "rejected"
    video.rejection_reason = request.form.get("reason", "").strip()[:5000]
    db.session.add(ModerationAudit(video_id=video.id, admin_id=current_user.id, action="reject", reason=video.rejection_reason))
    db.session.commit()
    flash("已拒绝。", "warning")
    return redirect(url_for("admin.dashboard", status=request.args.get("status", "")))
