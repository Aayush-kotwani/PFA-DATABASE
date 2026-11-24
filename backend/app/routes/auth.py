"""Authentication API routes."""

from apiflask import APIBlueprint

from app.schemas.auth import LoginInSchema, LoginOutSchema, UserMeOutSchema
from app.services.auth_service import authenticate_user
from app.utils.auth import get_current_user, login_required

auth_bp = APIBlueprint("auth", __name__, url_prefix="/api/auth", tag="Auth")


@auth_bp.post("/login")
@auth_bp.input(LoginInSchema)
@auth_bp.output(LoginOutSchema, status_code=200)
@auth_bp.doc(
    summary="User login",
    description="Authenticate with email and password to receive a JWT access token.",
)
def login(json_data):
    """Authenticate user and return JWT access token with account profile."""
    return authenticate_user(json_data["email"], json_data["password"])


@auth_bp.get("/me")
@auth_bp.output(UserMeOutSchema, status_code=200)
@auth_bp.doc(
    summary="Get current user profile",
    description="Retrieve account details of the currently authenticated user.",
    security="BearerAuth",
)
@login_required
def get_me():
    """Return profile details for the authenticated user."""
    return get_current_user()
