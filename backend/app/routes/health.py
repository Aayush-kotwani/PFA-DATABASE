"""Health check routes."""

from apiflask import APIBlueprint, Schema
from apiflask.fields import String
from flask import jsonify, make_response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

health_bp = APIBlueprint("health", __name__, url_prefix="/api", tag="Health")


class HealthOutSchema(Schema):
    """Response schema for the health check endpoint."""

    status = String(required=True, metadata={"example": "ok"})
    service = String(required=True, metadata={"example": "dog-sterilization-api"})
    database = String(required=False, metadata={"example": "connected"})


@health_bp.get("/health")
@health_bp.output(HealthOutSchema, status_code=200)
@health_bp.doc(
    summary="Health check",
    description="Verify that the API server is running and database is reachable.",
    responses={
        503: {
            "description": "Database unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "DATABASE_UNAVAILABLE",
                            "message": "Database connection failed",
                        }
                    }
                }
            },
        }
    },
)
def health_check():
    """Return status confirming server is alive and database is reachable."""
    try:
        db.session.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "service": "dog-sterilization-api",
            "database": "connected",
        }
    except SQLAlchemyError:
        return make_response(
            jsonify(
                {
                    "error": {
                        "code": "DATABASE_UNAVAILABLE",
                        "message": "Database connection failed",
                    }
                }
            ),
            503,
        )