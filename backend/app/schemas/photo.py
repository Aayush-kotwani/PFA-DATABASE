"""Schemas for Dog Photo upload and management endpoints."""

from apiflask import Schema
from apiflask.fields import Boolean, DateTime, File, Function, Integer, List, Nested, String
from apiflask.validators import OneOf

from app.services.storage import get_storage

PHOTO_TYPES = ("intake", "post_surgery", "release", "other")


class PhotoOutSchema(Schema):
    """Response schema for a dog photo record."""

    id = Integer(required=True, metadata={"example": 1})
    dog_id = Integer(required=True, metadata={"example": 1})
    case_id = Integer(allow_none=True, metadata={"example": 1})
    storage_key = String(required=True, metadata={"example": "dogs/1/abc123.webp"})
    url = Function(
        lambda obj: get_storage().get_url(obj.storage_key),
        required=True,
        metadata={"example": "http://localhost:5000/media/dogs/1/abc123.webp"},
    )
    photo_type = String(required=True, metadata={"example": "intake"})
    is_primary = Boolean(required=True, metadata={"example": True})
    uploaded_by = Integer(required=True)
    created_at = DateTime(required=True)
    updated_at = DateTime(required=True)


class PhotoListOutSchema(Schema):
    """List response for photos belonging to a dog."""

    items = List(Nested(PhotoOutSchema), required=True)


class PhotoUploadInSchema(Schema):
    """Multipart form + file schema for uploading a dog photo."""

    file = File(
        required=True,
        metadata={"description": "JPEG, PNG, or WebP image file (max 10 MB)"},
    )
    photo_type = String(
        load_default="intake",
        validate=OneOf(PHOTO_TYPES),
        metadata={"description": "Stage when photo was taken", "example": "intake"},
    )
    case_id = Integer(required=False, allow_none=True)
    is_primary = Boolean(
        load_default=False,
        metadata={"description": "Set as primary profile photo", "example": False},
    )


class PhotoUpdateInSchema(Schema):
    """Payload schema for updating photo metadata or primary flag."""

    photo_type = String(required=False, validate=OneOf(PHOTO_TYPES))
    is_primary = Boolean(required=False)
    case_id = Integer(required=False, allow_none=True)


class PhotoMessageOutSchema(Schema):
    """Standard message response for photo deletion."""

    message = String(required=True, metadata={"example": "Photo deleted successfully"})
