"""API route blueprints package."""

from app.routes.areas import areas_bp
from app.routes.auth import auth_bp
from app.routes.cases import cases_bp
from app.routes.dogs import dogs_bp
from app.routes.health import health_bp
from app.routes.users import users_bp

__all__ = ["areas_bp", "auth_bp", "cases_bp", "dogs_bp", "health_bp", "users_bp"]
