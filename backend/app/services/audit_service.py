"""Reusable audit logging and admin audit-log query services."""

from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.audit_log import AuditLog
from app.utils.pagination import paginate_query


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


def list_audit_logs(filters: dict[str, Any]) -> dict[str, Any]:
    """Retrieve paginated audit log entries with optional filters (Admin only)."""
    query = AuditLog.query.options(joinedload(AuditLog.user))

    if filters.get("user_id") is not None:
        query = query.filter(AuditLog.user_id == filters["user_id"])
    if filters.get("action"):
        query = query.filter(AuditLog.action == filters["action"])
    if filters.get("table_name"):
        query = query.filter(AuditLog.table_name == filters["table_name"].strip())
    if filters.get("record_id") is not None:
        query = query.filter(AuditLog.record_id == filters["record_id"])
    if filters.get("date_from"):
        start_dt = datetime.combine(filters["date_from"], time.min, tzinfo=timezone.utc)
        query = query.filter(AuditLog.created_at >= start_dt)
    if filters.get("date_to"):
        end_dt = datetime.combine(filters["date_to"], time.max, tzinfo=timezone.utc)
        query = query.filter(AuditLog.created_at <= end_dt)

    query = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    result = paginate_query(
        query,
        page=filters.get("page", 1),
        per_page=filters.get("per_page", 20),
    )

    result["items"] = [
        {
            "id": entry.id,
            "user_id": entry.user_id,
            "user_name": entry.user.name if entry.user else None,
            "action": entry.action,
            "table_name": entry.table_name,
            "record_id": entry.record_id,
            "changes": entry.changes,
            "created_at": entry.created_at,
        }
        for entry in result["items"]
    ]
    return result
