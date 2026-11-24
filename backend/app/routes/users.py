"""Admin-only User management API routes."""

from apiflask import APIBlueprint

from app.schemas.user import (
    UserCreateInSchema,
    UserListOutSchema,
    UserMessageOutSchema,
    UserOutSchema,
    UserResetPasswordInSchema,
    UserUpdateInSchema,
)
from app.services import user_service
from app.utils.auth import get_current_user, login_required, roles_required
from app.utils.pagination import PaginationQuerySchema

users_bp = APIBlueprint("users", __name__, url_prefix="/api/users", tag="Users")


@users_bp.get("", strict_slashes=False)
@users_bp.input(PaginationQuerySchema, location="query")
@users_bp.output(UserListOutSchema, status_code=200)
@users_bp.doc(
    summary="List users (Admin only)",
    description="Retrieve paginated list of all users.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def list_users(query_data):
    """Retrieve users with pagination."""
    return user_service.list_users(
        page=query_data.get("page", 1),
        per_page=query_data.get("per_page", 20),
    )


@users_bp.post("", strict_slashes=False)
@users_bp.input(UserCreateInSchema)
@users_bp.output(UserOutSchema, status_code=201)
@users_bp.doc(
    summary="Create user (Admin only)",
    description="Register a new staff user with an assigned role.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def create_user(json_data):
    """Create a new user."""
    current_user = get_current_user()
    return user_service.create_user(json_data, actor_id=current_user.id)


@users_bp.patch("/<int:user_id>")
@users_bp.input(UserUpdateInSchema)
@users_bp.output(UserOutSchema, status_code=200)
@users_bp.doc(
    summary="Update user (Admin only)",
    description="Modify a user's name, role, or active status.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def update_user(user_id, json_data):
    """Update existing user details."""
    current_user = get_current_user()
    return user_service.update_user(user_id, json_data, actor_id=current_user.id)


@users_bp.post("/<int:user_id>/reset-password")
@users_bp.input(UserResetPasswordInSchema)
@users_bp.output(UserMessageOutSchema, status_code=200)
@users_bp.doc(
    summary="Reset user password (Admin only)",
    description="Administratively reset a user's password.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def reset_password(user_id, json_data):
    """Reset password for a user."""
    current_user = get_current_user()
    return user_service.reset_user_password(
        user_id,
        new_password=json_data["new_password"],
        actor_id=current_user.id,
    )
