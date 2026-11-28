"""Rate-limit key extraction helpers for Flask-Limiter."""

from flask import g, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_limiter.util import get_remote_address


def get_user_or_ip_key() -> str:
    """Rate-limit key scoped by authenticated user ID, falling back to client IP."""
    user = getattr(g, "current_user", None)
    if user is not None:
        return f"user:{user.id}"

    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity is not None:
            return f"user:{identity}"
    except Exception:
        pass

    return get_remote_address()


def get_login_email_key() -> str:
    """Rate-limit key scoped by normalized login email, falling back to client IP."""
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        email = payload.get("email")
        if isinstance(email, str) and email.strip():
            return f"login_email:{email.strip().lower()}"
    return get_remote_address()
