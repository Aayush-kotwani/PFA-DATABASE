"""Security response headers middleware."""

from apiflask import APIFlask
from flask import request


def register_security_headers(app: APIFlask) -> None:
    """Register after_request handler applying baseline security headers."""

    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )

        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        elif request.path.startswith("/media/"):
            response.headers["Cache-Control"] = "private, max-age=3600"

        env_name = str(app.config.get("FLASK_ENV", "development")).strip().lower()
        if not app.testing and env_name == "production":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response
