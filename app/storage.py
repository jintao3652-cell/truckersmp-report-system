import os
from pathlib import Path


class LocalStorage:
    def __init__(self, root):
        self.root = Path(root)

    def put(self, source_path, key):
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source_path, target)
        return str(target)

    def delete(self, key):
        path = self.root / key
        if path.exists():
            path.unlink()

    def exists(self, key):
        return (self.root / key).exists()


class S3Storage:
    """S3/MinIO adapter; imported lazily so local deployments need no SDK."""
    def __init__(self, bucket, endpoint=None, region=None, prefix=""):
        import boto3
        self.bucket, self.prefix = bucket, prefix.strip("/")
        self.client = boto3.client("s3", endpoint_url=endpoint or None, region_name=region or None)

    def _key(self, key):
        if self.prefix and str(key).strip("/").startswith(self.prefix + "/"):
            return str(key).strip("/")
        return f"{self.prefix}/{key}" if self.prefix else key

    def put(self, source_path, key):
        self.client.upload_file(str(source_path), self.bucket, self._key(key))
        os.unlink(source_path)
        return self._key(key)

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=self._key(key))

    def exists(self, key):
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except Exception:
            return False

    def signed_url(self, key, expires=900):
        return self.client.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": self._key(key)}, ExpiresIn=expires)

    def download(self, key, target):
        self.client.download_file(self.bucket, self._key(key), str(target))

    def upload_key(self, source_path, key):
        self.client.upload_file(str(source_path), self.bucket, self._key(key))
        return self._key(key)


def get_storage(config):
    if config.get("STORAGE_BACKEND") == "s3":
        return S3Storage(config["STORAGE_S3_BUCKET"], config.get("STORAGE_S3_ENDPOINT"), config.get("STORAGE_S3_REGION"), config.get("STORAGE_S3_PREFIX", ""))
    return LocalStorage(config["VIDEO_FOLDER"])


def storage_key(path_or_name, config):
    """Return the object key for a DB path or filename."""
    value = str(path_or_name).replace("\\", "/")
    prefix = str(config.get("STORAGE_S3_PREFIX", "videos")).strip("/")
    if prefix and value.startswith(prefix + "/"):
        return value
    return value.lstrip("/")
