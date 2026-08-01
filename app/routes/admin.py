from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user

from .. import db
from ..models import Video

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
    videos = Video.query.order_by(Video.uploaded_at.desc()).limit(100).all()
    return render_template("admin_dashboard.html", videos=videos)


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
