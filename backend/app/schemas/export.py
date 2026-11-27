"""Schemas for Excel and Analytics export endpoints."""

from apiflask import Schema
from apiflask.fields import Boolean, String
from apiflask.validators import OneOf


class AnalyticsExportQuerySchema(Schema):
    """Query parameters for flat analytics export."""

    format = String(
        load_default="csv",
        validate=OneOf(["csv", "json"]),
        metadata={"description": "Export format: csv or json", "example": "csv"},
    )
    include_personal = Boolean(
        load_default=False,
        metadata={
            "description": "Include guardian contact and exact GPS coordinates (default False)",
            "example": False,
        },
    )
