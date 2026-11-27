"""API route blueprints package."""

from app.routes.areas import areas_bp
from app.routes.audit_logs import audit_logs_bp
from app.routes.auth import auth_bp
from app.routes.cases import cases_bp
from app.routes.dashboard import dashboard_bp
from app.routes.dogs import dogs_bp
from app.routes.exports import exports_bp
from app.routes.health import health_bp
from app.routes.photos import media_bp, photos_bp
from app.routes.public import public_bp
from app.routes.users import users_bp
from app.routes.vaccinations import vaccinations_bp, vaccinations_due_bp

__all__ = [
    "areas_bp",
    "audit_logs_bp",
    "auth_bp",
    "cases_bp",
    "dashboard_bp",
    "dogs_bp",
    "exports_bp",
    "health_bp",
    "media_bp",
    "photos_bp",
    "public_bp",
    "users_bp",
    "vaccinations_bp",
    "vaccinations_due_bp",
]
