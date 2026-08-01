import os
import argparse
import logging
from app.utils import utcnow

from app import create_app, db
from app.models import Video
from app.storage import get_storage

app = create_app()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Only report expired videos")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with app.app_context():
        expired = Video.query.filter(Video.expire_time < utcnow()).all()
        deleted = 0
        for video in expired:
            logging.info("Expired video id=%s path=%s", video.id, video.file_path)
            if args.dry_run:
                continue
            if app.config.get("STORAGE_BACKEND") == "s3":
                storage = get_storage(app.config)
                for key in (video.file_path, video.thumbnail_path):
                    if key:
                        try:
                            storage.delete(key)
                        except Exception:
                            logging.exception("Failed to remove object %s", key)
            else:
                for path in (video.file_path, video.thumbnail_path):
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                        except OSError:
                            logging.exception("Failed to remove %s", path)
            db.session.delete(video)
            deleted += 1
        if not args.dry_run:
            db.session.commit()
        print(f"Deleted {deleted} expired videos.")


if __name__ == "__main__":
    main()
