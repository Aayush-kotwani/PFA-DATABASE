"""Pytest fixtures configuration."""

import pytest
from app import create_app


@pytest.fixture
def app():
    """Create application instance for testing."""
    application = create_app()
    application.config.update({"TESTING": True})
    return application


@pytest.fixture
def client(app):
    """Create test client instance."""
    return app.test_client()
