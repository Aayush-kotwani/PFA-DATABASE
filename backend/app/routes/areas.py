"""Operational Areas management API routes."""

from apiflask import APIBlueprint

from app.schemas.area import (
    AreaCreateInSchema,
    AreaListOutSchema,
    AreaListQuerySchema,
    AreaOutSchema,
    AreaUpdateInSchema,
)
from app.services import area_service
from app.utils.auth import get_current_user, login_required, roles_required

areas_bp = APIBlueprint("areas", __name__, url_prefix="/api/areas", tag="Areas")


@areas_bp.get("", strict_slashes=False)
@areas_bp.input(AreaListQuerySchema, location="query")
@areas_bp.output(AreaListOutSchema, status_code=200)
@areas_bp.doc(
    summary="List operational areas",
    description="Retrieve paginated list of operational areas with optional active filter.",
    security="BearerAuth",
)
@login_required
def list_areas(query_data):
    """Retrieve all areas (available to all authenticated staff)."""
    return area_service.list_areas(
        page=query_data.get("page", 1),
        per_page=query_data.get("per_page", 20),
        is_active=query_data.get("is_active"),
    )


@areas_bp.get("/<int:area_id>")
@areas_bp.output(AreaOutSchema, status_code=200)
@areas_bp.doc(
    summary="Get area details",
    description="Retrieve details for a single operational area by ID.",
    security="BearerAuth",
)
@login_required
def get_area(area_id):
    """Retrieve single area by ID."""
    return area_service.get_area(area_id)


@areas_bp.post("", strict_slashes=False)
@areas_bp.input(AreaCreateInSchema)
@areas_bp.output(AreaOutSchema, status_code=201)
@areas_bp.doc(
    summary="Create operational area (Admin only)",
    description="Register a new geographic operational zone with a unique color hex and short code.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def create_area(json_data):
    """Create a new area."""
    current_user = get_current_user()
    return area_service.create_area(json_data, actor_id=current_user.id)


@areas_bp.patch("/<int:area_id>")
@areas_bp.input(AreaUpdateInSchema)
@areas_bp.output(AreaOutSchema, status_code=200)
@areas_bp.doc(
    summary="Update operational area (Admin only)",
    description="Modify area name, ward, landmark, feeder contacts, or color hex.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def update_area(area_id, json_data):
    """Update area details."""
    current_user = get_current_user()
    return area_service.update_area(area_id, json_data, actor_id=current_user.id)


@areas_bp.post("/<int:area_id>/deactivate")
@areas_bp.output(AreaOutSchema, status_code=200)
@areas_bp.doc(
    summary="Deactivate operational area (Admin only)",
    description="Set an area's is_active status to False.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def deactivate_area(area_id):
    """Deactivate an area."""
    current_user = get_current_user()
    return area_service.deactivate_area(area_id, actor_id=current_user.id)
