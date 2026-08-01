from flask import Blueprint, jsonify
from .api import videos, video_detail

api_v2_bp = Blueprint("api_v2", __name__, url_prefix="/api/v2")

@api_v2_bp.get("/videos")
def v2_videos():
    return videos()

@api_v2_bp.get("/videos/<int:video_id>")
def v2_video_detail(video_id):
    return video_detail(video_id)

@api_v2_bp.get("/")
def api_version():
    return jsonify({"version": "2", "deprecated": False})
