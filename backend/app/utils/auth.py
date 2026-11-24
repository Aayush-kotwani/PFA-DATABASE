"""Authentication and role authorization decorators."""

from functools import wraps
from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.extensions import db
from app.models.user import User
from app.utils.errors import APIError


def get_current_user() -> User | None:
    """Retrieve the currently authenticated user from Flask's request context."""
    return getattr(g, "current_user", None)


def login_required(fn):
    """Ensure request contains a valid JWT for an existing, active user."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        identity = get_jwt_identity()
        try:
            user_id = int(identity)
        except (ValueError, TypeError):
            raise APIError(401, "UNAUTHORIZED", "Invalid token identity")

        user = db.session.get(User, user_id)
        if not user:
            raise APIError(401, "UNAUTHORIZED", "User does not exist")
        if not user.is_active:
            raise APIError(403, "ACCOUNT_INACTIVE", "User account is inactive")

        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*allowed_roles: str):
    """Ensure the authenticated user possesses one of the allowed roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user or user.role not in allowed_roles:
                raise APIError(403, "FORBIDDEN", "Insufficient permissions")
            return fn(*args, **kwargs)

        return wrapper

    return decorator
