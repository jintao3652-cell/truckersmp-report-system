"""Verify the append-only moderation audit hash chain."""
from app import create_app, db
from app.models import ModerationAudit
from app.utils import audit_hash

app = create_app()
with app.app_context():
    previous = None
    rows = ModerationAudit.query.order_by(ModerationAudit.id).all()
    for row in rows:
        if row.previous_hash != previous:
            raise SystemExit(f"chain break at audit {row.id}")
        if row.record_hash and row.record_hash != audit_hash(row.previous_hash, row):
            raise SystemExit(f"hash mismatch at audit {row.id}")
        previous = row.record_hash
    print(f"Audit chain OK: {len(rows)} records")
