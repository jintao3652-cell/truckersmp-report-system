import os
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .. import db
from ..models import LoginAudit, Video

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
    videos = query.limit(100).all()
    logins = LoginAudit.query.order_by(LoginAudit.created_at.desc()).limit(200).all()
    return render_template("admin_dashboard.html", videos=videos, logins=logins)


@admin_bp.post("/delete/<int:video_id>")
def delete(video_id):
    video = Video.query.get_or_404(video_id)
    for path in (video.file_path, video.thumbnail_path):
        if path and os.path.exists(path):
            os.remove(path)
    db.session.delete(video)
    db.session.commit()
    flash("视频及其文件已删除。", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/approve/<int:video_id>")
def approve(video_id):
    video = Video.query.get_or_404(video_id)
    video.status = "approved"
    db.session.commit()
    flash("已通过。", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/reject/<int:video_id>")
def reject(video_id):
    video = Video.query.get_or_404(video_id)
    video.status = "rejected"
    db.session.commit()
    flash("已拒绝。", "warning")
    return redirect(url_for("admin.dashboard"))
