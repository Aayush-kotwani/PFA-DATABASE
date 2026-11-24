"""Authentication request and response schemas."""

from apiflask import Schema
from apiflask.fields import Boolean, DateTime, Email, Integer, Nested, String


class LoginInSchema(Schema):
    """Schema for user credentials submitted during login."""

    email = Email(
        required=True,
        metadata={"description": "User email address", "example": "admin@ngo.org"},
    )
    password = String(
        required=True,
        load_only=True,
        metadata={"description": "User account password", "example": "change-me-admin-password"},
    )


class UserMeOutSchema(Schema):
    """Schema for current user account profile details."""

    id = Integer(required=True, metadata={"example": 1})
    name = String(required=True, metadata={"example": "NGO Admin"})
    email = String(required=True, metadata={"example": "admin@ngo.org"})
    role = String(required=True, metadata={"example": "admin"})
    is_active = Boolean(required=True, metadata={"example": True})
    created_at = DateTime(required=True)


class LoginOutSchema(Schema):
    """Schema for successful authentication response with JWT access token."""

    access_token = String(required=True, metadata={"description": "JWT bearer token"})
    token_type = String(required=True, dump_default="bearer", metadata={"example": "bearer"})
    user = Nested(UserMeOutSchema, required=True)
