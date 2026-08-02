from pathlib import Path


def test_api_uses_public_media_url_for_local_approved_shares():
    source = Path("app/routes/api.py").read_text(encoding="utf-8")
    assert 'url_for("video.shared_media", share_code=video.share_code, _external=True)' in source


def test_web_upload_always_enters_chunk_path_when_javascript_is_available():
    source = Path("app/static/js/upload.js").read_text(encoding="utf-8")
    assert "file.size < 16 * 1024 * 1024" not in source
