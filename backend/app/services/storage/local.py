"""Local filesystem storage backend for development."""

from pathlib import Path

from app.services.storage.base import StorageBackend
from app.utils.errors import APIError


class LocalStorage(StorageBackend):
    """Stores media files on local disk inside `upload_dir`."""

    def __init__(self, upload_dir: str | Path, public_base_url: str) -> None:
        self.upload_dir = Path(upload_dir).resolve()
        self.public_base_url = public_base_url.rstrip("/")

    def _safe_path(self, key: str) -> Path:
        """Resolve `key` inside `upload_dir` while blocking path traversal."""
        clean_key = key.lstrip("/\\")
        if not clean_key:
            raise APIError(400, "INVALID_STORAGE_KEY", "Storage key cannot be empty")
        target = (self.upload_dir / clean_key).resolve()
        if not target.is_relative_to(self.upload_dir) or target == self.upload_dir:
            raise APIError(400, "INVALID_STORAGE_KEY", "Invalid storage key path")
        return target

    def save(self, key: str, data: bytes, content_type: str = "image/webp") -> str:
        """Write file bytes to local disk and return the storage key."""
        target = self._safe_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return key

    def delete(self, key: str) -> None:
        """Delete the local file if it exists."""
        target = self._safe_path(key)
        if target.is_file():
            target.unlink()

    def get_url(self, key: str) -> str:
        """Return the local `/media/<key>` URL."""
        clean_key = key.lstrip("/")
        return f"{self.public_base_url}/media/{clean_key}"
