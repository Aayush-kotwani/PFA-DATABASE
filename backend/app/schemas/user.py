"""Schemas for User management endpoints."""

from apiflask import Schema
from apiflask.fields import Boolean, DateTime, Email, Integer, List, Nested, String
from apiflask.validators import Length, OneOf


class UserOutSchema(Schema):
    """Response schema for a single user record."""

    id = Integer(required=True, metadata={"example": 1})
    name = String(required=True, metadata={"example": "NGO Admin"})
    email = String(required=True, metadata={"example": "admin@ngo.org"})
    role = String(required=True, metadata={"example": "admin"})
    is_active = Boolean(required=True, metadata={"example": True})
    created_at = DateTime(required=True)
    updated_at = DateTime(required=True)


class UserListOutSchema(Schema):
    """Paginated list response for users."""

    items = List(Nested(UserOutSchema), required=True)
    page = Integer(required=True, metadata={"example": 1})
    per_page = Integer(required=True, metadata={"example": 20})
    total = Integer(required=True, metadata={"example": 2})


class UserCreateInSchema(Schema):
    """Payload schema for creating a new user (Admin only)."""

    name = String(
        required=True,
        validate=Length(min=1, max=100),
        metadata={"description": "Full name of the user", "example": "Aarav Sharma"},
    )
    email = Email(
        required=True,
        validate=Length(max=120),
        metadata={"description": "Unique email address", "example": "aarav@ngo.org"},
    )
    password = String(
        required=True,
        load_only=True,
        validate=Length(min=8),
        metadata={"description": "Account password (min 8 characters)", "example": "SecurePass123!"},
    )
    role = String(
        load_default="volunteer",
        validate=OneOf(["admin", "volunteer"]),
        metadata={"description": "User permission role", "example": "volunteer"},
    )
    is_active = Boolean(
        load_default=True,
        metadata={"description": "Whether the account is active", "example": True},
    )


class UserUpdateInSchema(Schema):
    """Payload schema for updating existing user details (Admin only)."""

    name = String(
        required=False,
        validate=Length(min=1, max=100),
        metadata={"description": "Updated name of the user", "example": "Aarav K. Sharma"},
    )
    role = String(
        required=False,
        validate=OneOf(["admin", "volunteer"]),
        metadata={"description": "Updated permission role", "example": "admin"},
    )
    is_active = Boolean(
        required=False,
        metadata={"description": "Updated account active status", "example": False},
    )


class UserResetPasswordInSchema(Schema):
    """Payload schema for administrative password reset."""

    new_password = String(
        required=True,
        load_only=True,
        validate=Length(min=8),
        metadata={"description": "New account password (min 8 characters)", "example": "NewSecurePass123!"},
    )


class UserMessageOutSchema(Schema):
    """Standard message response for user actions."""

    message = String(required=True, metadata={"example": "Password reset successfully"})
