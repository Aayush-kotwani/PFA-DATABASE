"""Authentication domain services."""

import logging

from flask import request
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash

from app.models.user import User
from app.utils.errors import APIError

logger = logging.getLogger(__name__)


def authenticate_user(email: str, password: str) -> dict:
    """Authenticate a user by email and password, returning access token and profile."""
    normalized_email = email.strip().lower()
    user = User.query.filter_by(email=normalized_email).first()

    if not user or not check_password_hash(user.password_hash, password):
        logger.warning(
            "Failed login attempt for email=%s ip=%s",
            normalized_email,
            request.remote_addr,
        )
        raise APIError(401, "INVALID_CREDENTIALS", "Invalid email or password")

    if not user.is_active:
        logger.warning(
            "Inactive account login attempt for email=%s ip=%s",
            normalized_email,
            request.remote_addr,
        )
        raise APIError(403, "ACCOUNT_INACTIVE", "User account is inactive")

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"token_version": user.token_version},
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }
