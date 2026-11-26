"""Storage backend factory and exports."""

from pathlib import Path
from flask import current_app

from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalStorage
from app.utils.errors import APIError


def resolve_upload_dir() -> Path:
    """Resolve UPLOAD_DIR relative to the backend root if not already absolute."""
    raw_dir = Path(current_app.config["UPLOAD_DIR"])
    if raw_dir.is_absolute():
        return raw_dir.resolve()
    return (Path(current_app.root_path).parent / raw_dir).resolve()


def get_storage() -> StorageBackend:
    """Instantiate and return the configured storage backend."""
    backend = current_app.config.get("STORAGE_BACKEND", "local").strip().lower()
    if backend == "local":
        return LocalStorage(
            upload_dir=resolve_upload_dir(),
            public_base_url=current_app.config["PUBLIC_BASE_URL"],
        )
    if backend == "r2":
        raise APIError(500, "STORAGE_NOT_CONFIGURED", "R2 storage is not configured yet")
    raise APIError(500, "STORAGE_NOT_CONFIGURED", f"Unsupported storage backend: {backend}")


__all__ = ["StorageBackend", "LocalStorage", "get_storage", "resolve_upload_dir"]
