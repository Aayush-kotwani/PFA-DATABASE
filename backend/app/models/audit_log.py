"""Audit log model for immutable tracking of database mutations."""

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from app.extensions import db


class AuditLog(db.Model):
    """Immutable audit trail recording creates, updates, and deletes with JSON diffs."""

    __tablename__ = "audit_logs"

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(String(20), nullable=False)  # 'create', 'update', 'delete'
    table_name = db.Column(String(50), nullable=False, index=True)
    record_id = db.Column(Integer, nullable=False, index=True)

    # JSONB on PostgreSQL for efficient querying, standard JSON as fallback
    changes = db.Column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    created_at = db.Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        index=True,
    )

    # Relationship
    user = db.relationship("User", backref="audit_logs")

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action='{self.action}' "
            f"table='{self.table_name}' record_id={self.record_id}>"
        )
