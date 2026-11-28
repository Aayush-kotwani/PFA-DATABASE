"""Dog Photos CRUD and local media serving routes."""

from apiflask import APIBlueprint
from flask import current_app, send_from_directory

from app.extensions import limiter
from app.schemas.photo import (
    PhotoListOutSchema,
    PhotoMessageOutSchema,
    PhotoOutSchema,
    PhotoUpdateInSchema,
    PhotoUploadInSchema,
)
from app.services import photo_service
from app.services.storage import resolve_upload_dir
from app.utils.auth import get_current_user, login_required, roles_required
from app.utils.errors import APIError
from app.utils.rate_limit import get_user_or_ip_key

photos_bp = APIBlueprint(
    "photos",
    __name__,
    url_prefix="/api/dogs/<int:dog_id>/photos",
    tag="Photos",
)

media_bp = APIBlueprint("media", __name__, tag="Media")


@photos_bp.get("", strict_slashes=False)
@photos_bp.output(PhotoListOutSchema, status_code=200)
@photos_bp.doc(
    summary="List photos for a dog",
    description="Retrieve all non-deleted photos for a dog, ordered with primary photo first.",
    security="BearerAuth",
)
@login_required
def list_photos(dog_id):
    """List active photos for a dog."""
    return photo_service.list_photos(dog_id)


@photos_bp.post("", strict_slashes=False)
@limiter.limit(lambda: current_app.config["RATELIMIT_PHOTO_UPLOAD"], key_func=get_user_or_ip_key)
@photos_bp.input(PhotoUploadInSchema, location="files")
@photos_bp.output(PhotoOutSchema, status_code=201)
@photos_bp.doc(
    summary="Upload a dog photo",
    description="Upload a JPEG/PNG/WebP photo (max 10 MB). Fixes EXIF rotation, strips metadata, resizes <=1200px, converts to WebP.",
    security="BearerAuth",
)
@login_required
def upload_photo(dog_id, files_data):
    """Upload and process a dog photo."""
    current_user = get_current_user()
    file_storage = files_data.get("file")
    meta = {
        "photo_type": files_data.get("photo_type", "intake"),
        "case_id": files_data.get("case_id"),
        "is_primary": files_data.get("is_primary", False),
    }
    return photo_service.upload_photo(dog_id, file_storage, meta, actor=current_user)


@photos_bp.patch("/<int:photo_id>")
@photos_bp.input(PhotoUpdateInSchema)
@photos_bp.output(PhotoOutSchema, status_code=200)
@photos_bp.doc(
    summary="Update photo metadata or primary flag",
    description="Update photo_type, case_id, or mark a photo as primary.",
    security="BearerAuth",
)
@login_required
def update_photo(dog_id, photo_id, json_data):
    """Update photo metadata."""
    current_user = get_current_user()
    return photo_service.update_photo(dog_id, photo_id, json_data, actor=current_user)


@photos_bp.delete("/<int:photo_id>")
@photos_bp.output(PhotoMessageOutSchema, status_code=200)
@photos_bp.doc(
    summary="Soft-delete photo (Admin only)",
    description="Mark a dog photo record as soft-deleted.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def delete_photo(dog_id, photo_id):
    """Soft-delete a dog photo."""
    current_user = get_current_user()
    return photo_service.soft_delete_photo(dog_id, photo_id, actor=current_user)


@media_bp.get("/media/<path:key>")
@media_bp.doc(
    summary="Serve local media file (Development only)",
    description="Serve uploaded images from UPLOAD_DIR when STORAGE_BACKEND is 'local'.",
)
def serve_local_media(key):
    """Serve stored local files securely during development."""
    if current_app.config.get("STORAGE_BACKEND", "local").strip().lower() != "local":
        raise APIError(404, "NOT_FOUND", "Local media serving is disabled")

    upload_dir = resolve_upload_dir()
    clean_key = key.lstrip("/\\")
    target = (upload_dir / clean_key).resolve()
    if not target.is_relative_to(upload_dir) or not target.is_file():
        raise APIError(404, "NOT_FOUND", "Media file not found")

    return send_from_directory(upload_dir, clean_key)
