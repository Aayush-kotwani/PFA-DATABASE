"""Schemas for Dog management endpoints."""

from apiflask import Schema
from apiflask.fields import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    List,
    Nested,
    String,
)
from apiflask.validators import Length, OneOf, Range
from marshmallow import post_dump

from app.utils.auth import get_current_user
from app.utils.pagination import PaginationQuerySchema

DOG_SEXES = ("male", "female", "unknown")
DOG_STATUSES = (
    "registered",
    "picked_up",
    "in_surgery",
    "recovering",
    "released",
    "deceased",
    "lost",
)
DOG_AGE_GROUPS = ("puppy", "young", "adult", "senior")
DOG_BODY_CONDITIONS = ("underweight", "normal", "overweight")


class DogAreaSummarySchema(Schema):
    """Embedded area summary returned with dog records."""

    id = Integer(required=True, metadata={"example": 1})
    name = String(required=True, metadata={"example": "Central Zone - Ward 1"})
    short_code = String(required=True, metadata={"example": "CTR"})
    color_name = String(required=True, metadata={"example": "Teal"})
    color_hex = String(required=True, metadata={"example": "#0D9488"})


class DogOutSchema(Schema):
    """Response schema for a dog record with role-based guardian_phone filtering."""

    id = Integer(required=True, metadata={"example": 1})
    dog_code = String(required=True, metadata={"example": "CTR-0001"})
    public_token = String(required=True)
    area_id = Integer(required=True, metadata={"example": 1})
    area = Nested(DogAreaSummarySchema, required=True)

    sex = String(required=True, metadata={"example": "female"})
    approx_age = String(allow_none=True, metadata={"example": "2 years"})
    age_group = String(allow_none=True, metadata={"example": "adult"})
    coat_description = String(allow_none=True, metadata={"example": "Brown and white short coat"})
    weight_kg = Float(allow_none=True, metadata={"example": 14.5})
    body_condition = String(allow_none=True, metadata={"example": "normal"})
    is_pregnant = Boolean(allow_none=True, metadata={"example": False})
    temperament = String(allow_none=True, metadata={"example": "Friendly, calm"})

    guardian_name = String(allow_none=True, metadata={"example": "Ramesh Kumar"})
    guardian_phone = String(allow_none=True, metadata={"example": "+91-98765-00001"})

    capture_address = String(allow_none=True, metadata={"example": "Behind Main Market Gate"})
    landmark = String(allow_none=True, metadata={"example": "Near Municipal Clock Tower"})
    latitude = Float(allow_none=True, metadata={"example": 19.0760})
    longitude = Float(allow_none=True, metadata={"example": 72.8777})
    maps_url = String(
        allow_none=True,
        metadata={"example": "https://www.google.com/maps?q=19.076000,72.877700"},
    )

    ear_notch_done = Boolean(required=True, metadata={"example": False})
    status = String(required=True, metadata={"example": "registered"})
    medical_conditions = String(allow_none=True)
    medical_history = String(allow_none=True)

    created_by = Integer(required=True)
    updated_by = Integer(allow_none=True)
    created_at = DateTime(required=True)
    updated_at = DateTime(required=True)

    @post_dump
    def format_dog_output(self, data: dict, **kwargs) -> dict:
        """Strip guardian_phone for non-admins and round GPS coordinates to 6 decimals."""
        user = get_current_user()
        if not user or user.role != "admin":
            data.pop("guardian_phone", None)
        for coord in ("latitude", "longitude"):
            if data.get(coord) is not None:
                data[coord] = round(float(data[coord]), 6)
        return data


class DogListQuerySchema(PaginationQuerySchema):
    """Query parameters for searching and filtering dogs."""

    search = String(
        required=False,
        metadata={"description": "Search dog_code, guardian_name, or landmark"},
    )
    area_id = Integer(required=False, metadata={"description": "Filter by area ID"})
    status = String(
        required=False,
        validate=OneOf(DOG_STATUSES),
        metadata={"description": "Filter by dog status"},
    )
    sex = String(
        required=False,
        validate=OneOf(DOG_SEXES),
        metadata={"description": "Filter by sex"},
    )
    created_from = Date(
        required=False,
        metadata={"description": "Filter created_at >= YYYY-MM-DD", "example": "2026-01-01"},
    )
    created_to = Date(
        required=False,
        metadata={"description": "Filter created_at <= YYYY-MM-DD", "example": "2026-12-31"},
    )


class DogListOutSchema(Schema):
    """Paginated list response for dogs."""

    items = List(Nested(DogOutSchema), required=True)
    page = Integer(required=True, metadata={"example": 1})
    per_page = Integer(required=True, metadata={"example": 20})
    total = Integer(required=True, metadata={"example": 1})


class DogCreateInSchema(Schema):
    """Payload schema for registering a new dog."""

    area_id = Integer(required=True, metadata={"example": 1})
    sex = String(load_default="unknown", validate=OneOf(DOG_SEXES))
    approx_age = String(required=False, allow_none=True, validate=Length(max=30))
    age_group = String(required=False, allow_none=True, validate=OneOf(DOG_AGE_GROUPS))
    coat_description = String(required=False, allow_none=True, validate=Length(max=200))
    weight_kg = Float(required=False, allow_none=True, validate=Range(min=0, max=150))
    body_condition = String(required=False, allow_none=True, validate=OneOf(DOG_BODY_CONDITIONS))
    is_pregnant = Boolean(required=False, allow_none=True)
    temperament = String(required=False, allow_none=True)

    guardian_name = String(required=False, allow_none=True, validate=Length(max=100))
    guardian_phone = String(required=False, allow_none=True, validate=Length(max=20))

    capture_address = String(required=False, allow_none=True)
    landmark = String(required=False, allow_none=True, validate=Length(max=200))
    latitude = Float(required=False, allow_none=True, validate=Range(min=-90, max=90))
    longitude = Float(required=False, allow_none=True, validate=Range(min=-180, max=180))

    ear_notch_done = Boolean(load_default=False)
    status = String(load_default="registered", validate=OneOf(DOG_STATUSES))
    medical_conditions = String(required=False, allow_none=True)
    medical_history = String(required=False, allow_none=True)


class DogUpdateInSchema(Schema):
    """Payload schema for updating an existing dog."""

    sex = String(required=False, validate=OneOf(DOG_SEXES))
    approx_age = String(required=False, allow_none=True, validate=Length(max=30))
    age_group = String(required=False, allow_none=True, validate=OneOf(DOG_AGE_GROUPS))
    coat_description = String(required=False, allow_none=True, validate=Length(max=200))
    weight_kg = Float(required=False, allow_none=True, validate=Range(min=0, max=150))
    body_condition = String(required=False, allow_none=True, validate=OneOf(DOG_BODY_CONDITIONS))
    is_pregnant = Boolean(required=False, allow_none=True)
    temperament = String(required=False, allow_none=True)

    guardian_name = String(required=False, allow_none=True, validate=Length(max=100))
    # Accepted in payload; ignored for volunteers at service layer
    guardian_phone = String(required=False, allow_none=True, validate=Length(max=20))

    capture_address = String(required=False, allow_none=True)
    landmark = String(required=False, allow_none=True, validate=Length(max=200))
    latitude = Float(required=False, allow_none=True, validate=Range(min=-90, max=90))
    longitude = Float(required=False, allow_none=True, validate=Range(min=-180, max=180))

    ear_notch_done = Boolean(required=False)
    status = String(required=False, validate=OneOf(DOG_STATUSES))
    medical_conditions = String(required=False, allow_none=True)
    medical_history = String(required=False, allow_none=True)


class DogMessageOutSchema(Schema):
    """Standard message response for dog deletion."""

    message = String(required=True, metadata={"example": "Dog deleted successfully"})
