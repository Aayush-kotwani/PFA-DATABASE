"""Cases management API routes nested under a dog."""

from apiflask import APIBlueprint

from app.schemas.case import (
    CaseCreateInSchema,
    CaseListOutSchema,
    CaseMessageOutSchema,
    CaseOutSchema,
    CaseUpdateInSchema,
)
from app.services import case_service
from app.utils.auth import get_current_user, login_required, roles_required
from app.utils.pagination import PaginationQuerySchema

cases_bp = APIBlueprint(
    "cases", __name__, url_prefix="/api/dogs/<int:dog_id>/cases", tag="Cases"
)


@cases_bp.get("", strict_slashes=False)
@cases_bp.input(PaginationQuerySchema, location="query")
@cases_bp.output(CaseListOutSchema, status_code=200)
@cases_bp.doc(
    summary="List cases for a dog",
    description="Retrieve paginated list of non-deleted cases for a specific dog.",
    security="BearerAuth",
)
@login_required
def list_cases(dog_id, query_data):
    """Retrieve paginated cases for a dog."""
    return case_service.list_cases(
        dog_id=dog_id,
        page=query_data.get("page", 1),
        per_page=query_data.get("per_page", 20),
    )


@cases_bp.post("", strict_slashes=False)
@cases_bp.input(CaseCreateInSchema)
@cases_bp.output(CaseOutSchema, status_code=201)
@cases_bp.doc(
    summary="Create a case for a dog",
    description="Record a new pickup/surgery/release case under a dog.",
    security="BearerAuth",
)
@login_required
def create_case(dog_id, json_data):
    """Create a new case for a dog."""
    current_user = get_current_user()
    return case_service.create_case(dog_id, json_data, actor=current_user)


@cases_bp.get("/<int:case_id>")
@cases_bp.output(CaseOutSchema, status_code=200)
@cases_bp.doc(
    summary="Get case details",
    description="Retrieve a single non-deleted case belonging to a dog.",
    security="BearerAuth",
)
@login_required
def get_case(dog_id, case_id):
    """Retrieve a single case by ID."""
    return case_service.get_case(dog_id, case_id)


@cases_bp.patch("/<int:case_id>")
@cases_bp.input(CaseUpdateInSchema)
@cases_bp.output(CaseOutSchema, status_code=200)
@cases_bp.doc(
    summary="Update a case",
    description="Update surgery, prescription, outcome, or drop details on a case.",
    security="BearerAuth",
)
@login_required
def update_case(dog_id, case_id, json_data):
    """Update an existing case."""
    current_user = get_current_user()
    return case_service.update_case(dog_id, case_id, json_data, actor=current_user)


@cases_bp.delete("/<int:case_id>")
@cases_bp.output(CaseMessageOutSchema, status_code=200)
@cases_bp.doc(
    summary="Soft-delete case (Admin only)",
    description="Mark a case record as soft-deleted.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def delete_case(dog_id, case_id):
    """Soft-delete a case."""
    current_user = get_current_user()
    return case_service.soft_delete_case(dog_id, case_id, actor=current_user)
