from pathlib import Path


def test_api_review_notifications_do_not_reference_reason_in_approve_path():
    source = Path("app/routes/api.py").read_text(encoding="utf-8")
    approve_block = source.split('@api_bp.post("/videos/<int:video_id>/approve")', 1)[1].split('@api_bp.post("/videos/<int:video_id>/reject")', 1)[0]
    assert '"Video approved"' in approve_block
    assert "reason" not in approve_block
