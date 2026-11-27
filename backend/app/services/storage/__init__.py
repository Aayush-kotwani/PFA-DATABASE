"""Storage backend factory and exports."""

from pathlib import Path
from flask import current_app

from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalStorage
from app.services.storage.r2 import R2Storage
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
        endpoint_url = current_app.config.get("R2_ENDPOINT_URL", "").strip()
        bucket_name = current_app.config.get("R2_BUCKET_NAME", "").strip()
        access_key_id = current_app.config.get("R2_ACCESS_KEY_ID", "").strip()
        secret_access_key = current_app.config.get("R2_SECRET_ACCESS_KEY", "").strip()
        expiry = int(current_app.config.get("R2_PRESIGNED_URL_EXPIRY", 3600))

        if not all([endpoint_url, bucket_name, access_key_id, secret_access_key]):
            raise APIError(
                500,
                "STORAGE_NOT_CONFIGURED",
                "R2 storage credentials are missing in environment configuration",
            )

        return R2Storage(
            endpoint_url=endpoint_url,
            bucket_name=bucket_name,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            presigned_expiry=expiry,
        )

    raise APIError(500, "STORAGE_NOT_CONFIGURED", f"Unsupported storage backend: {backend}")


__all__ = ["StorageBackend", "LocalStorage", "R2Storage", "get_storage", "resolve_upload_dir"]
