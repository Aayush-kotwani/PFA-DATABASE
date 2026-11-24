"""Schemas for Area management endpoints."""

from apiflask import Schema
from apiflask.fields import Boolean, DateTime, Integer, List, Nested, String
from apiflask.validators import Length, Regexp

from app.utils.pagination import PaginationQuerySchema

HEX_COLOR_REGEX = r"^#[0-9A-Fa-f]{6}$"


class AreaOutSchema(Schema):
    """Response schema for an operational area."""

    id = Integer(required=True, metadata={"example": 1})
    name = String(required=True, metadata={"example": "Central Zone - Ward 1"})
    short_code = String(required=True, metadata={"example": "CTR"})
    ward_no = String(required=True, metadata={"example": "Ward 1"})
    color_name = String(required=True, metadata={"example": "Teal"})
    color_hex = String(required=True, metadata={"example": "#0D9488"})
    landmark = String(allow_none=True, metadata={"example": "Near Municipal Clock Tower"})
    animal_lover_name = String(allow_none=True, metadata={"example": "Sunita Sharma"})
    animal_lover_phone = String(allow_none=True, metadata={"example": "+91-98765-43210"})
    last_dog_number = Integer(required=True, metadata={"example": 0})
    is_active = Boolean(required=True, metadata={"example": True})
    created_at = DateTime(required=True)
    updated_at = DateTime(required=True)


class AreaListQuerySchema(PaginationQuerySchema):
    """Query parameter schema for filtering areas."""

    is_active = Boolean(
        required=False,
        metadata={"description": "Filter by active status (optional)", "example": True},
    )


class AreaListOutSchema(Schema):
    """Paginated list response for areas."""

    items = List(Nested(AreaOutSchema), required=True)
    page = Integer(required=True, metadata={"example": 1})
    per_page = Integer(required=True, metadata={"example": 20})
    total = Integer(required=True, metadata={"example": 3})


class AreaCreateInSchema(Schema):
    """Payload schema for creating a new operational area."""

    name = String(
        required=True,
        validate=Length(min=1, max=120),
        metadata={"description": "Full name of the area", "example": "West Suburb - Ward 4"},
    )
    short_code = String(
        required=True,
        validate=Length(min=1, max=10),
        metadata={"description": "Short code used in dog codes (max 10 chars)", "example": "WST"},
    )
    ward_no = String(
        required=True,
        validate=Length(min=1, max=20),
        metadata={"description": "Municipal ward number/identifier", "example": "Ward 4"},
    )
    color_name = String(
        required=True,
        validate=Length(min=1, max=30),
        metadata={"description": "Human-readable color description", "example": "Emerald"},
    )
    color_hex = String(
        required=True,
        validate=Regexp(HEX_COLOR_REGEX, error="Color hex must be in valid format #RRGGBB"),
        metadata={"description": "Unique color hex code in format #RRGGBB", "example": "#10B981"},
    )
    landmark = String(
        required=False,
        allow_none=True,
        validate=Length(max=200),
        metadata={"description": "Key landmark in this area", "example": "Near West Gate Bus Stop"},
    )
    animal_lover_name = String(
        required=False,
        allow_none=True,
        validate=Length(max=100),
        metadata={"description": "Local volunteer or feeder contact name", "example": "Deepak Mehta"},
    )
    animal_lover_phone = String(
        required=False,
        allow_none=True,
        validate=Length(max=20),
        metadata={"description": "Feeder contact phone number", "example": "+91-98765-43213"},
    )


class AreaUpdateInSchema(Schema):
    """Payload schema for updating an existing area (never exposes last_dog_number)."""

    name = String(
        required=False,
        validate=Length(min=1, max=120),
        metadata={"description": "Updated area name", "example": "West Suburb Extension"},
    )
    short_code = String(
        required=False,
        validate=Length(min=1, max=10),
        metadata={"description": "Updated short code", "example": "WSX"},
    )
    ward_no = String(
        required=False,
        validate=Length(min=1, max=20),
        metadata={"description": "Updated ward number", "example": "Ward 4A"},
    )
    color_name = String(
        required=False,
        validate=Length(min=1, max=30),
        metadata={"description": "Updated color name", "example": "Forest Green"},
    )
    color_hex = String(
        required=False,
        validate=Regexp(HEX_COLOR_REGEX, error="Color hex must be in valid format #RRGGBB"),
        metadata={"description": "Updated unique color hex code", "example": "#059669"},
    )
    landmark = String(
        required=False,
        allow_none=True,
        validate=Length(max=200),
        metadata={"description": "Updated landmark", "example": "Near Metro Station Pillar 12"},
    )
    animal_lover_name = String(
        required=False,
        allow_none=True,
        validate=Length(max=100),
        metadata={"description": "Updated feeder contact name"},
    )
    animal_lover_phone = String(
        required=False,
        allow_none=True,
        validate=Length(max=20),
        metadata={"description": "Updated feeder contact phone"},
    )
    is_active = Boolean(
        required=False,
        metadata={"description": "Active status for dog assignments", "example": True},
    )
