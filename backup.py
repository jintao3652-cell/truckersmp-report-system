"""Create a consistent database and video backup archive."""
import argparse
import os
import sqlite3
import tarfile
from pathlib import Path
from app import create_app

app = create_app()
parser = argparse.ArgumentParser()
parser.add_argument("destination", help="backup directory")
args = parser.parse_args()
with app.app_context():
    dest = Path(args.destination).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / f"truckersmp-backup-{__import__('datetime').datetime.utcnow().strftime('%Y%m%d%H%M%S')}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        db_url = app.config["SQLALCHEMY_DATABASE_URI"]
        if db_url.startswith("sqlite:///"):
            db_path = Path(db_url[10:])
            if db_path.exists():
                tar.add(db_path, arcname="database.sqlite")
        video_dir = Path(app.config["VIDEO_FOLDER"])
        if video_dir.exists() and app.config.get("STORAGE_BACKEND") == "local":
            tar.add(video_dir, arcname="videos")
    print(archive)
