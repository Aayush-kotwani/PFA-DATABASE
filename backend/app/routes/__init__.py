"""API route blueprints package."""

from app.routes.areas import areas_bp
from app.routes.auth import auth_bp
from app.routes.health import health_bp
from app.routes.users import users_bp

__all__ = ["areas_bp", "auth_bp", "health_bp", "users_bp"]
