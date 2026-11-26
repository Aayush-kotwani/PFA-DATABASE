"""Vaccinations management and due-date tracking API routes."""

from apiflask import APIBlueprint

from app.schemas.vaccination import (
    DueVaccinationQuerySchema,
    DueVaccinationsOutSchema,
    VaccinationCreateInSchema,
    VaccinationListOutSchema,
    VaccinationMessageOutSchema,
    VaccinationOutSchema,
    VaccinationUpdateInSchema,
)
from app.services import vaccination_service
from app.utils.auth import get_current_user, login_required, roles_required
from app.utils.pagination import PaginationQuerySchema

vaccinations_bp = APIBlueprint(
    "vaccinations",
    __name__,
    url_prefix="/api/dogs/<int:dog_id>/vaccinations",
    tag="Vaccinations",
)

vaccinations_due_bp = APIBlueprint(
    "vaccinations_due",
    __name__,
    url_prefix="/api/vaccinations",
    tag="Vaccinations",
)


@vaccinations_bp.get("", strict_slashes=False)
@vaccinations_bp.input(PaginationQuerySchema, location="query")
@vaccinations_bp.output(VaccinationListOutSchema, status_code=200)
@vaccinations_bp.doc(
    summary="List vaccinations for a dog",
    description="Retrieve paginated list of non-deleted vaccinations for a specific dog.",
    security="BearerAuth",
)
@login_required
def list_vaccinations(dog_id, query_data):
    """Retrieve paginated vaccinations for a dog."""
    return vaccination_service.list_vaccinations(
        dog_id=dog_id,
        page=query_data.get("page", 1),
        per_page=query_data.get("per_page", 20),
    )


@vaccinations_bp.post("", strict_slashes=False)
@vaccinations_bp.input(VaccinationCreateInSchema)
@vaccinations_bp.output(VaccinationOutSchema, status_code=201)
@vaccinations_bp.doc(
    summary="Record a vaccination for a dog",
    description="Create a new vaccination record under a dog.",
    security="BearerAuth",
)
@login_required
def create_vaccination(dog_id, json_data):
    """Create a new vaccination record."""
    current_user = get_current_user()
    return vaccination_service.create_vaccination(dog_id, json_data, actor=current_user)


@vaccinations_bp.get("/<int:vaccination_id>")
@vaccinations_bp.output(VaccinationOutSchema, status_code=200)
@vaccinations_bp.doc(
    summary="Get vaccination details",
    description="Retrieve a single non-deleted vaccination belonging to a dog.",
    security="BearerAuth",
)
@login_required
def get_vaccination(dog_id, vaccination_id):
    """Retrieve a single vaccination by ID."""
    return vaccination_service.get_vaccination(dog_id, vaccination_id)


@vaccinations_bp.patch("/<int:vaccination_id>")
@vaccinations_bp.input(VaccinationUpdateInSchema)
@vaccinations_bp.output(VaccinationOutSchema, status_code=200)
@vaccinations_bp.doc(
    summary="Update a vaccination",
    description="Update vaccination fields such as batch_no, next_due_date, or notes.",
    security="BearerAuth",
)
@login_required
def update_vaccination(dog_id, vaccination_id, json_data):
    """Update an existing vaccination record."""
    current_user = get_current_user()
    return vaccination_service.update_vaccination(
        dog_id, vaccination_id, json_data, actor=current_user
    )


@vaccinations_bp.delete("/<int:vaccination_id>")
@vaccinations_bp.output(VaccinationMessageOutSchema, status_code=200)
@vaccinations_bp.doc(
    summary="Soft-delete vaccination (Admin only)",
    description="Mark a vaccination record as soft-deleted.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def delete_vaccination(dog_id, vaccination_id):
    """Soft-delete a vaccination record."""
    current_user = get_current_user()
    return vaccination_service.soft_delete_vaccination(
        dog_id, vaccination_id, actor=current_user
    )


@vaccinations_due_bp.get("/due")
@vaccinations_due_bp.input(DueVaccinationQuerySchema, location="query")
@vaccinations_due_bp.output(DueVaccinationsOutSchema, status_code=200)
@vaccinations_due_bp.doc(
    summary="Get overdue and upcoming vaccinations",
    description="List overdue vaccinations and those due within the next N days.",
    security="BearerAuth",
)
@login_required
def get_due_vaccinations(query_data):
    """Return overdue and upcoming vaccinations."""
    return vaccination_service.get_due_vaccinations(days=query_data.get("days", 30))
