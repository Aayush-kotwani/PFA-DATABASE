"""Application factory for the Dog Sterilization Management System."""

import os
from apiflask import APIFlask
from flask import jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Config, validate_secret_strength
from app.extensions import cors, db, jwt, limiter, migrate
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
from app.utils.errors import register_error_handlers
from app.utils.logging import configure_logging
from app.utils.security_headers import register_security_headers


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

    # Enforce strong non-placeholder secrets in production (SEC-03)
    env_name = os.getenv("FLASK_ENV", app.config.get("FLASK_ENV", "development")).strip().lower()
    if not app.testing and env_name == "production":
        validate_secret_strength("SECRET_KEY", app.config.get("SECRET_KEY", ""))
        validate_secret_strength("JWT_SECRET_KEY", app.config.get("JWT_SECRET_KEY", ""))

    # Apply ProxyFix behind reverse proxies such as Render (SEC-05)
    if not app.testing:
        proxy_count = int(app.config.get("PROXY_FIX_COUNT", 1))
        if proxy_count > 0:
            app.wsgi_app = ProxyFix(
                app.wsgi_app,
                x_for=proxy_count,
                x_proto=proxy_count,
                x_host=proxy_count,
                x_prefix=proxy_count,
            )

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

    # Initialize Flask-Migrate database migrations
    migrate.init_app(app, db)

    # Initialize Flask-JWT-Extended authentication
    jwt.init_app(app)

    # Initialize Flask-Limiter rate limiting (SEC-01)
    limiter.init_app(app)

    @jwt.unauthorized_loader
    def unauthorized_callback(reason: str):
        return jsonify({"error": {"code": "UNAUTHORIZED", "message": reason}}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason: str):
        return jsonify({"error": {"code": "UNAUTHORIZED", "message": reason}}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": {"code": "UNAUTHORIZED", "message": "Token has expired"}}), 401

    # Configure structured logging and request correlation IDs (SEC-10)
    configure_logging(app)

    # Register centralized error handlers and APIFlask error processor
    register_error_handlers(app)

    # Register security response headers (SEC-06)
    register_security_headers(app)

    # Register database models with SQLAlchemy metadata
    from app import models  # noqa: F401

    # Enable CORS for API routes
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(areas_bp)
    app.register_blueprint(dogs_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(vaccinations_bp)
    app.register_blueprint(vaccinations_due_bp)
    app.register_blueprint(photos_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(audit_logs_bp)
    app.register_blueprint(exports_bp)

    return app
