"""Schemas for Admin-only Audit Log listing."""

from apiflask import Schema
from apiflask.fields import Date, DateTime, Integer, List, Nested, Raw, String
from apiflask.validators import OneOf

from app.utils.pagination import PaginationQuerySchema


class AuditLogQuerySchema(PaginationQuerySchema):
    """Query parameters for filtering audit log entries."""

    user_id = Integer(required=False, metadata={"description": "Filter by actor user ID"})
    action = String(
        required=False,
        validate=OneOf(["create", "update", "delete"]),
        metadata={"description": "Filter by mutation action"},
    )
    table_name = String(
        required=False,
        metadata={"description": "Filter by target table name", "example": "dogs"},
    )
    record_id = Integer(required=False, metadata={"description": "Filter by target record ID"})
    date_from = Date(required=False, metadata={"description": "Filter created_at >= YYYY-MM-DD"})
    date_to = Date(required=False, metadata={"description": "Filter created_at <= YYYY-MM-DD"})


class AuditLogOutSchema(Schema):
    """Response schema for a single audit log entry."""

    id = Integer(required=True)
    user_id = Integer(allow_none=True)
    user_name = String(allow_none=True, metadata={"example": "NGO Admin"})
    action = String(required=True, metadata={"example": "create"})
    table_name = String(required=True, metadata={"example": "dogs"})
    record_id = Integer(required=True)
    changes = Raw(allow_none=True)
    created_at = DateTime(required=True)


class AuditLogListOutSchema(Schema):
    """Paginated list response for audit logs."""

    items = List(Nested(AuditLogOutSchema), required=True)
    page = Integer(required=True, metadata={"example": 1})
    per_page = Integer(required=True, metadata={"example": 20})
    total = Integer(required=True, metadata={"example": 10})
