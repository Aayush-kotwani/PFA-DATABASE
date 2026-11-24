"""Application factory for the Dog Sterilization Management System."""

from apiflask import APIFlask

from app.config import Config
from app.extensions import cors, db
from app.routes.health import health_bp


def create_app(config_class: type[Config] = Config) -> APIFlask:
    """Create and configure the APIFlask application instance."""
    app = APIFlask(
        __name__,
        title="Dog Sterilization Management API",
        version="0.1.0",
        docs_path="/docs",
        spec_path="/openapi.json",
    )
    app.config.from_object(config_class)

    # Configure Bearer JWT security scheme so Swagger UI shows the Authorize button
    app.security_schemes = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    # Initialize SQLAlchemy database extension
    db.init_app(app)

    # Register database models with SQLAlchemy metadata
    from app import models  # noqa: F401

    # Enable CORS for API routes
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # Register blueprints
    app.register_blueprint(health_bp)

    return app