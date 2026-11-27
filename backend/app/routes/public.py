"""Unauthenticated public dog verification routes."""

from apiflask import APIBlueprint

from app.schemas.public import PublicDogOutSchema
from app.services import public_service

public_bp = APIBlueprint("public", __name__, url_prefix="/api/public", tag="Public")


@public_bp.get("/dogs/<string:public_token>")
@public_bp.output(PublicDogOutSchema, status_code=200)
@public_bp.doc(
    summary="Get public dog verification info",
    description="Unauthenticated endpoint for QR scan pages. Returns only non-sensitive status, area, photo, and latest vaccination.",
)
def get_public_dog(public_token):
    """Return limited public details for a dog by its public_token."""
    return public_service.get_public_dog_info(public_token)
