"""Pytest fixtures using an isolated in-memory SQLite database (never touches Neon)."""

import os
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models.area import Area
from app.models.user import User


@pytest.fixture
def app(tmp_path):
    """Create isolated application instance with fresh in-memory SQLite DB per test."""
    application = create_app(TestingConfig)
    application.config.update({"UPLOAD_DIR": str(tmp_path / "uploads")})

    with application.app_context():
        db.create_all()

        # Seed baseline users and areas into the isolated test DB
        admin_email = os.getenv("ADMIN_EMAIL", "admin@ngo.org")
        admin_pass = os.getenv("ADMIN_PASSWORD", "AdminPass123!")
        vol_email = os.getenv("VOLUNTEER_EMAIL", "volunteer@ngo.org")
        vol_pass = os.getenv("VOLUNTEER_PASSWORD", "VolunteerPass123!")

        db.session.add_all(
            [
                User(
                    name="NGO Admin",
                    email=admin_email,
                    password_hash=generate_password_hash(admin_pass),
                    role="admin",
                    is_active=True,
                ),
                User(
                    name="NGO Volunteer",
                    email=vol_email,
                    password_hash=generate_password_hash(vol_pass),
                    role="volunteer",
                    is_active=True,
                ),
                Area(
                    name="Central Zone - Ward 1",
                    short_code="CTR",
                    ward_no="Ward 1",
                    color_name="Teal",
                    color_hex="#0D9488",
                    landmark="Near Municipal Clock Tower",
                    last_dog_number=0,
                    is_active=True,
                ),
                Area(
                    name="North Market - Ward 2",
                    short_code="NMT",
                    ward_no="Ward 2",
                    color_name="Amber",
                    color_hex="#D97706",
                    landmark="Opposite Vegetable Wholesale Yard",
                    last_dog_number=0,
                    is_active=True,
                ),
                Area(
                    name="Station Road - Ward 3",
                    short_code="STR",
                    ward_no="Ward 3",
                    color_name="Indigo",
                    color_hex="#4F46E5",
                    landmark="Platform 1 Auto Stand Gate",
                    last_dog_number=0,
                    is_active=True,
                ),
            ]
        )
        db.session.commit()

    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client instance."""
    return app.test_client()


@pytest.fixture
def admin_headers(client) -> dict[str, str]:
    """Authenticate as admin and return Authorization header."""
    email = os.getenv("ADMIN_EMAIL", "admin@ngo.org")
    password = os.getenv("ADMIN_PASSWORD", "AdminPass123!")
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.get_json()['access_token']}"}


@pytest.fixture
def volunteer_headers(client) -> dict[str, str]:
    """Authenticate as volunteer and return Authorization header."""
    email = os.getenv("VOLUNTEER_EMAIL", "volunteer@ngo.org")
    password = os.getenv("VOLUNTEER_PASSWORD", "VolunteerPass123!")
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.get_json()['access_token']}"}


@pytest.fixture
def sample_area(app) -> Area:
    """Return the seeded CTR area from the isolated test DB."""
    with app.app_context():
        return Area.query.filter_by(short_code="CTR").first()
