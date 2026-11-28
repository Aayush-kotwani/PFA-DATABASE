"""Authentication domain services."""

import logging

from flask import request
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.user import User
from app.services.audit_service import log_audit
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


def change_password(user: User, current_password: str, new_password: str) -> dict[str, str]:
    """Verify current password, update hash, revoke old JWTs, and audit log."""
    if not check_password_hash(user.password_hash, current_password):
        logger.warning(
            "Failed password change attempt for user_id=%s ip=%s",
            user.id,
            request.remote_addr,
        )
        raise APIError(401, "INVALID_CREDENTIALS", "Current password is incorrect")

    if new_password == current_password:
        raise APIError(
            400,
            "BAD_REQUEST",
            "New password must be different from current password",
        )

    try:
        user.password_hash = generate_password_hash(new_password)
        user.token_version += 1
        log_audit(
            action="update",
            table_name="users",
            record_id=user.id,
            user_id=user.id,
            changes={"password_changed": True},
        )
        db.session.commit()
        logger.info("User changed password: user_id=%s", user.id)
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return {"message": "Password changed successfully"}
