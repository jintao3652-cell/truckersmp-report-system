"""Restore a local SQLite/video backup archive after explicit confirmation."""
import argparse
import tarfile
from pathlib import Path
from app import create_app

app = create_app()
parser = argparse.ArgumentParser()
parser.add_argument("archive")
parser.add_argument("--target", required=True)
args = parser.parse_args()
target = Path(args.target).resolve()
target.mkdir(parents=True, exist_ok=True)
with tarfile.open(args.archive, "r:gz") as tar:
    members = tar.getmembers()
    for member in members:
        destination = (target / member.name).resolve()
        if target != destination and target not in destination.parents:
            raise ValueError("unsafe archive path")
    tar.extractall(target, members=members)
print(f"Restored backup into {target}")
