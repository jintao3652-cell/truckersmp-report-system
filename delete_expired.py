import os
from datetime import datetime, timezone

from app import create_app, db
from app.models import Video

app = create_app()


def main():
    with app.app_context():
        expired = Video.query.filter(Video.expire_time < datetime.now(timezone.utc)).all()
        deleted = 0
        for video in expired:
            if video.file_path and os.path.exists(video.file_path):
                os.remove(video.file_path)
            db.session.delete(video)
            deleted += 1
        db.session.commit()
        print(f"Deleted {deleted} expired videos.")


if __name__ == "__main__":
    main()
