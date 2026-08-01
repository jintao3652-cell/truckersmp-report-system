from datetime import timedelta
import os

from app import create_app, db
from app.models import UploadSession
from app.utils import utcnow

app = create_app()

with app.app_context():
    cutoff = utcnow() - timedelta(seconds=app.config["UPLOAD_SESSION_EXPIRES_SECONDS"])
    sessions = UploadSession.query.filter(UploadSession.updated_at < cutoff, UploadSession.status == "active").all()
    for session in sessions:
        if os.path.exists(session.temp_path):
            os.remove(session.temp_path)
        session.status = "expired"
    db.session.commit()
    print(f"Expired upload sessions: {len(sessions)}")
