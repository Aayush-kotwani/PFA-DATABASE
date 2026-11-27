"""Business logic services for Dog Photo management."""

from typing import Any
import uuid

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.case import Case
from app.models.dog import Dog
from app.models.dog_photo import DogPhoto
from app.models.user import User
from app.services.audit_service import log_audit
from app.services.storage import get_storage
from app.utils.errors import APIError
from app.utils.images import process_uploaded_image


def _get_active_dog(dog_id: int) -> Dog:
    """Return a non-deleted Dog by ID or raise 404."""
    dog = Dog.query.filter(Dog.id == dog_id, Dog.is_deleted.is_(False)).first()
    if not dog:
        raise APIError(404, "NOT_FOUND", "Dog not found")
    return dog


def _get_active_photo(dog_id: int, photo_id: int) -> DogPhoto:
    """Verify parent dog is active, then return non-deleted DogPhoto or raise 404."""
    _get_active_dog(dog_id)
    photo = DogPhoto.query.filter(
        DogPhoto.id == photo_id,
        DogPhoto.dog_id == dog_id,
        DogPhoto.is_deleted.is_(False),
    ).first()
    if not photo:
        raise APIError(404, "NOT_FOUND", "Photo not found")
    return photo


def _validate_case_link(dog_id: int, case_id: int | None) -> None:
    """Ensure optional case_id belongs to the given dog and is not soft-deleted."""
    if case_id is None:
        return
    case = Case.query.filter(
        Case.id == case_id,
        Case.dog_id == dog_id,
        Case.is_deleted.is_(False),
    ).first()
    if not case:
        raise APIError(400, "INVALID_CASE", "Case not found for this dog")


def _clear_primary_flag(dog_id: int, exclude_photo_id: int | None = None) -> None:
    """Unset is_primary on all other active photos for a dog."""
    query = DogPhoto.query.filter(
        DogPhoto.dog_id == dog_id,
        DogPhoto.is_deleted.is_(False),
        DogPhoto.is_primary.is_(True),
    )
    if exclude_photo_id is not None:
        query = query.filter(DogPhoto.id != exclude_photo_id)
    query.update({"is_primary": False}, synchronize_session=False)


def list_photos(dog_id: int) -> dict[str, list[DogPhoto]]:
    """List all non-deleted photos for a dog, primary first."""
    _get_active_dog(dog_id)
    items = (
        DogPhoto.query.filter(
            DogPhoto.dog_id == dog_id,
            DogPhoto.is_deleted.is_(False),
        )
        .order_by(DogPhoto.is_primary.desc(), DogPhoto.created_at.desc(), DogPhoto.id.desc())
        .all()
    )
    return {"items": items}


def upload_photo(
    dog_id: int,
    file_storage: Any,
    meta: dict[str, Any],
    actor: User,
) -> DogPhoto:
    """Validate, process to WebP, store, and record a dog photo."""
    _get_active_dog(dog_id)
    max_photos = int(current_app.config.get("MAX_PHOTOS_PER_DOG", 15))
    active_count = DogPhoto.query.filter_by(dog_id=dog_id, is_deleted=False).count()
    if active_count >= max_photos:
        raise APIError(
            409,
            "PHOTO_LIMIT_REACHED",
            f"Maximum of {max_photos} active photos per dog reached",
        )

    case_id = meta.get("case_id")
    _validate_case_link(dog_id, case_id)

    webp_bytes = process_uploaded_image(file_storage)

    has_existing = (
        DogPhoto.query.filter(
            DogPhoto.dog_id == dog_id,
            DogPhoto.is_deleted.is_(False),
        ).first()
        is not None
    )
    # First active photo for a dog automatically becomes primary
    is_primary = bool(meta.get("is_primary")) or (not has_existing)

    key = f"dogs/{dog_id}/{uuid.uuid4().hex}.webp"
    storage = get_storage()
    storage.save(key, webp_bytes, "image/webp")

    photo = DogPhoto(
        dog_id=dog_id,
        case_id=case_id,
        storage_key=key,
        photo_type=meta.get("photo_type", "intake"),
        is_primary=is_primary,
        uploaded_by=actor.id,
    )

    try:
        if is_primary:
            _clear_primary_flag(dog_id)
        db.session.add(photo)
        db.session.flush()

        log_audit(
            action="create",
            table_name="dog_photos",
            record_id=photo.id,
            user_id=actor.id,
            changes={
                "dog_id": photo.dog_id,
                "case_id": photo.case_id,
                "photo_type": photo.photo_type,
                "is_primary": photo.is_primary,
                "storage_key": photo.storage_key,
            },
        )
        db.session.commit()
        db.session.refresh(photo)
    except SQLAlchemyError:
        db.session.rollback()
        storage.delete(key)
        raise

    return photo


def update_photo(
    dog_id: int,
    photo_id: int,
    data: dict[str, Any],
    actor: User,
) -> DogPhoto:
    """Update photo_type, case_id, or primary status."""
    photo = _get_active_photo(dog_id, photo_id)

    if "case_id" in data and data["case_id"] != photo.case_id:
        _validate_case_link(dog_id, data["case_id"])

    diff: dict[str, Any] = {}
    for field in ("photo_type", "case_id", "is_primary"):
        if field in data:
            old_val = getattr(photo, field)
            new_val = data[field]
            if old_val != new_val:
                diff[field] = {"old": old_val, "new": new_val}
                setattr(photo, field, new_val)

    if diff:
        try:
            if data.get("is_primary") is True:
                _clear_primary_flag(dog_id, exclude_photo_id=photo.id)
            log_audit(
                action="update",
                table_name="dog_photos",
                record_id=photo.id,
                user_id=actor.id,
                changes=diff,
            )
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise

    return photo


def soft_delete_photo(dog_id: int, photo_id: int, actor: User) -> dict[str, str]:
    """Soft-delete a dog photo (Admin only)."""
    photo = _get_active_photo(dog_id, photo_id)

    try:
        was_primary = photo.is_primary
        photo.soft_delete()
        photo.is_primary = False
        changes: dict[str, Any] = {"is_deleted": {"old": False, "new": True}}
        if was_primary:
            changes["is_primary"] = {"old": True, "new": False}

        log_audit(
            action="delete",
            table_name="dog_photos",
            record_id=photo.id,
            user_id=actor.id,
            changes=changes,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return {"message": "Photo deleted successfully"}
