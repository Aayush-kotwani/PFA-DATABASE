"""Reusable audit logging service."""

from typing import Any
from app.extensions import db
from app.models.audit_log import AuditLog


def log_audit(
    action: str,
    table_name: str,
    record_id: int,
    user_id: int | None = None,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    """Record an audit log entry in the current database session.

    Never commits directly so it remains part of the caller's atomic transaction.
    """
    log_entry = AuditLog(
        action=action,
        table_name=table_name,
        record_id=record_id,
        user_id=user_id,
        changes=changes,
    )
    db.session.add(log_entry)
    return log_entry
