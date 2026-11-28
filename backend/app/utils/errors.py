"""Standardized API exception classes and error handlers."""

import logging
from typing import Any
from apiflask import HTTPError
from flask import jsonify, Response
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom application exception with HTTP status code and error code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str) -> tuple[Response, int]:
    """Return a standardized JSON error response."""
    return jsonify({
        "error": {
            "code": code,
            "message": message,
        }
    }), status_code


def _format_validation_detail(detail: Any) -> str:
    """Format Marshmallow/APIFlask validation detail into a readable error message."""
    if isinstance(detail, dict):
        messages = []
        for location, field_errors in detail.items():
            if isinstance(field_errors, dict):
                for field, errs in field_errors.items():
                    err_str = ", ".join(errs) if isinstance(errs, list) else str(errs)
                    messages.append(f"{field}: {err_str}")
            elif isinstance(field_errors, list):
                messages.append(", ".join(field_errors))
            else:
                messages.append(str(field_errors))
        if messages:
            return "; ".join(messages)
    return str(detail)


def register_error_handlers(app) -> None:
    """Register APIFlask error processor and global exception handlers."""

    @app.error_processor
    def process_http_error(error: HTTPError):
        """Format APIFlask HTTPError exceptions (including 422 schema validation)."""
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            413: "FILE_TOO_LARGE",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_SERVER_ERROR",
        }
        code = code_map.get(error.status_code, "HTTP_ERROR")
        message = error.message

        if error.status_code == 422 and error.detail:
            formatted = _format_validation_detail(error.detail)
            message = f"Validation failed: {formatted}"

        return {
            "error": {
                "code": code,
                "message": message,
            }
        }, error.status_code, error.headers

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """Format custom APIError exceptions."""
        return error_response(error.status_code, error.code, error.message)

    @app.errorhandler(413)
    def handle_413(error):
        """Format oversized request payload errors (exceeding MAX_CONTENT_LENGTH)."""
        return error_response(413, "FILE_TOO_LARGE", "Image exceeds 10 MB limit")

    @app.errorhandler(429)
    def handle_429(error):
        """Format rate-limit exceeded errors while preserving Retry-After header."""
        resp, status = error_response(
            429,
            "RATE_LIMIT_EXCEEDED",
            "Too many requests. Please try again later.",
        )
        if hasattr(error, "get_headers"):
            for header_name, header_val in error.get_headers():
                if header_name.lower() == "retry-after":
                    resp.headers[header_name] = header_val
        return resp, status

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        """Log unexpected exceptions with traceback and return safe generic JSON."""
        if isinstance(error, HTTPException):
            return error_response(
                error.code or 500,
                "HTTP_ERROR",
                error.description or "HTTP error",
            )
        logger.exception("Unhandled exception: %s", error)
        return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")

    @app.errorhandler(500)
    def handle_500(error):
        """Format unexpected 500 server errors."""
        return error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected server error occurred.")
