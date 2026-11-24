"""Reusable database model mixins for timestamps and soft delete."""

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, func
from app.extensions import db


class TimestampMixin:
    """Provides created_at and updated_at tracking for models."""

    created_at = db.Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        doc="Timestamp when the record was created",
    )
    updated_at = db.Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        doc="Timestamp when the record was last updated",
    )


class SoftDeleteMixin:
    """Provides is_deleted flag and deleted_at timestamp for soft deletion."""

    is_deleted = db.Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Flag indicating if record has been soft-deleted",
    )
    deleted_at = db.Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when the record was soft-deleted",
    )

    def soft_delete(self) -> None:
        """Mark this entity as deleted without removing the row from the database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
