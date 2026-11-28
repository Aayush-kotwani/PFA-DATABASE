"""Structured application logging with per-request correlation IDs."""

import logging
import uuid

from apiflask import APIFlask
from flask import g, has_request_context, request


class RequestIDFilter(logging.Filter):
    """Attach the current request_id (or '-') to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if has_request_context():
            record.request_id = getattr(g, "request_id", "-")
        else:
            record.request_id = "-"
        return True


def configure_logging(app: APIFlask) -> None:
    """Configure request ID tracking and structured log formatting."""
    request_filter = RequestIDFilter()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [req=%(request_id)s] %(name)s: %(message)s"
    )

    root_logger = logging.getLogger("app")
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.addFilter(request_filter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
            if not any(isinstance(f, RequestIDFilter) for f in handler.filters):
                handler.addFilter(request_filter)

    root_logger.setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)

    @app.before_request
    def assign_request_id():
        incoming_id = request.headers.get("X-Request-ID", "").strip()
        g.request_id = incoming_id[:64] if incoming_id else uuid.uuid4().hex[:12]

    @app.after_request
    def attach_request_id_header(response):
        response.headers.setdefault("X-Request-ID", getattr(g, "request_id", "-"))
        return response
