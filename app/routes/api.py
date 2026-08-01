import secrets
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from ..models import Video

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

@api_bp.get("/videos")
@login_required
def videos():
    query = Video.query if current_user.is_admin else Video.query.filter_by(uploader_id=current_user.id)
    return jsonify([{"id": v.id, "title": v.title, "status": v.status, "file_size": v.file_size, "duration": v.duration} for v in query.order_by(Video.uploaded_at.desc()).limit(100)])
