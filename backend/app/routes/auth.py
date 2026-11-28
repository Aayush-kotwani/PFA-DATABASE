"""Authentication API routes."""

from apiflask import APIBlueprint
from flask import current_app
from flask_limiter.util import get_remote_address

from app.extensions import limiter
from app.schemas.auth import (
    AuthMessageOutSchema,
    ChangePasswordInSchema,
    LoginInSchema,
    LoginOutSchema,
    UserMeOutSchema,
)
from app.services.auth_service import authenticate_user, change_password
from app.utils.auth import get_current_user, login_required
from app.utils.rate_limit import get_login_email_key, get_user_or_ip_key

auth_bp = APIBlueprint("auth", __name__, url_prefix="/api/auth", tag="Auth")


@auth_bp.post("/login")
@limiter.limit(lambda: current_app.config["RATELIMIT_LOGIN_IP"], key_func=get_remote_address)
@limiter.limit(lambda: current_app.config["RATELIMIT_LOGIN_EMAIL"], key_func=get_login_email_key)
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


@auth_bp.post("/change-password")
@limiter.limit(
    lambda: current_app.config["RATELIMIT_CHANGE_PASSWORD"],
    key_func=get_user_or_ip_key,
)
@auth_bp.input(ChangePasswordInSchema)
@auth_bp.output(AuthMessageOutSchema, status_code=200)
@auth_bp.doc(
    summary="Change own password",
    description="Verify current password, update password, and revoke existing JWTs.",
    security="BearerAuth",
)
@login_required
def change_own_password(json_data):
    """Change password for the currently authenticated user."""
    return change_password(
        get_current_user(),
        json_data["current_password"],
        json_data["new_password"],
    )
