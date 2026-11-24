"""Reusable pagination schemas and helpers for API lists."""

from typing import Any
from apiflask import Schema
from apiflask.fields import Integer
from apiflask.validators import Range
from app.extensions import db


class PaginationQuerySchema(Schema):
    """Query parameter schema for paginated list endpoints."""

    page = Integer(
        load_default=1,
        validate=Range(min=1),
        metadata={"description": "Page number (1-based index)", "example": 1},
    )
    per_page = Integer(
        load_default=20,
        validate=Range(min=1, max=100),
        metadata={"description": "Number of items per page (1-100)", "example": 20},
    )


def paginate_query(query: Any, page: int = 1, per_page: int = 20) -> dict[str, Any]:
    """Execute pagination on a SQLAlchemy Query or Select statement.

    Returns a standardized dictionary containing items, page, per_page, and total.
    Supports both Model.query (Query.paginate) and db.select statements (db.paginate).
    """
    if hasattr(query, "paginate"):
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    else:
        pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return {
        "items": list(pagination.items),
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
    }
