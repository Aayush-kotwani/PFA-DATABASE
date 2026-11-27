"""Business logic services for User management."""

import logging
from typing import Any
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.user import User
from app.services.audit_service import log_audit
from app.utils.errors import APIError
from app.utils.pagination import paginate_query

logger = logging.getLogger(__name__)


def list_users(page: int = 1, per_page: int = 20) -> dict[str, Any]:
    """Retrieve paginated list of users ordered by ID ascending."""
    query = User.query.order_by(User.id.asc())
    return paginate_query(query, page=page, per_page=per_page)


def create_user(data: dict[str, Any], actor_id: int) -> User:
    """Create a new user with hashed password and audit trail logging."""
    normalized_email = data["email"].strip().lower()
    existing = User.query.filter_by(email=normalized_email).first()
    if existing:
        raise APIError(409, "CONFLICT", "A user with this email already exists")

    user = User(
        name=data["name"].strip(),
        email=normalized_email,
        password_hash=generate_password_hash(data["password"]),
        role=data.get("role", "volunteer"),
        is_active=data.get("is_active", True),
    )

    try:
        db.session.add(user)
        db.session.flush()  # Populate user.id for audit log

        log_audit(
            action="create",
            table_name="users",
            record_id=user.id,
            user_id=actor_id,
            changes={
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
            },
        )
        db.session.commit()
        logger.info(
            "User created: actor_id=%s target_id=%s role=%s",
            actor_id,
            user.id,
            user.role,
        )
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return user


def update_user(user_id: int, data: dict[str, Any], actor_id: int) -> User:
    """Update user details (name, role, active status) with audit trail diff logging."""
    # Prevent admin from deactivating or demoting their own account
    if user_id == actor_id and (data.get("is_active") is False or data.get("role") == "volunteer"):
        raise APIError(400, "BAD_REQUEST", "Admins cannot deactivate or demote their own account")

    user = db.session.get(User, user_id)
    if not user:
        raise APIError(404, "NOT_FOUND", "User not found")

    diff: dict[str, Any] = {}
    for field in ["name", "role", "is_active"]:
        if field in data and data[field] is not None:
            old_val = getattr(user, field)
            new_val = data[field].strip() if isinstance(data[field], str) else data[field]
            if old_val != new_val:
                diff[field] = {"old": old_val, "new": new_val}
                setattr(user, field, new_val)

    if diff:
        try:
            # Revoke existing tokens on role change or deactivation
            if "role" in diff or ("is_active" in diff and user.is_active is False):
                user.token_version += 1

            log_audit(
                action="update",
                table_name="users",
                record_id=user.id,
                user_id=actor_id,
                changes=diff,
            )
            db.session.commit()
            if "role" in diff or "is_active" in diff:
                logger.warning(
                    "User security attributes updated: actor_id=%s target_id=%s fields=%s",
                    actor_id,
                    user.id,
                    sorted(diff.keys()),
                )
        except SQLAlchemyError:
            db.session.rollback()
            raise

    return user


def reset_user_password(user_id: int, new_password: str, actor_id: int) -> dict[str, str]:
    """Reset a user's password with audit trail logging (no plaintext stored)."""
    user = db.session.get(User, user_id)
    if not user:
        raise APIError(404, "NOT_FOUND", "User not found")

    try:
        user.password_hash = generate_password_hash(new_password)
        user.token_version += 1
        log_audit(
            action="update",
            table_name="users",
            record_id=user.id,
            user_id=actor_id,
            changes={"password_reset": True},
        )
        db.session.commit()
        logger.warning(
            "User password reset: actor_id=%s target_id=%s",
            actor_id,
            user.id,
        )
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return {"message": "Password reset successfully"}
