"""Health check routes."""

from apiflask import APIBlueprint, Schema
from apiflask.fields import String

health_bp = APIBlueprint("health", __name__, url_prefix="/api", tag="Health")


class HealthOutSchema(Schema):
    """Response schema for the health check endpoint."""

    status = String(required=True, metadata={"example": "ok"})
    service = String(required=True, metadata={"example": "dog-sterilization-api"})


@health_bp.get("/health")
@health_bp.output(HealthOutSchema, status_code=200)
@health_bp.doc(summary="Health check", description="Verify that the API server is running.")
def health_check():
    """Return a simple status payload confirming the server is alive."""
    return {"status": "ok", "service": "dog-sterilization-api"}