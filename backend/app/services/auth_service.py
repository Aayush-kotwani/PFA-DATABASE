"""Authentication domain services."""

from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash

from app.models.user import User
from app.utils.errors import APIError


def authenticate_user(email: str, password: str) -> dict:
    """Authenticate a user by email and password, returning access token and profile."""
    normalized_email = email.strip().lower()
    user = User.query.filter_by(email=normalized_email).first()

    if not user or not check_password_hash(user.password_hash, password):
        raise APIError(401, "INVALID_CREDENTIALS", "Invalid email or password")

    if not user.is_active:
        raise APIError(403, "ACCOUNT_INACTIVE", "User account is inactive")

    token = create_access_token(identity=str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }
