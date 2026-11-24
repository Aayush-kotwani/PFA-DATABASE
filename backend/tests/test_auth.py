"""Tests for authentication and authorization (Step B1)."""

import os
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.user import User


def test_health_check(client):
    """Health check endpoint should return 200 with database connected."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_login_success(client):
    """Valid credentials should return JWT access token and user profile."""
    email = os.getenv("ADMIN_EMAIL", "admin@ngo.org")
    password = os.getenv("ADMIN_PASSWORD", "change-me-admin-password")

    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email
    assert data["user"]["role"] == "admin"


def test_login_invalid_password(client):
    """Wrong password should return 401 with INVALID_CREDENTIALS."""
    email = os.getenv("ADMIN_EMAIL", "admin@ngo.org")

    response = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_validation_error(client):
    """Invalid email format should return 422 with VALIDATION_ERROR."""
    response = client.post("/api/auth/login", json={"email": "not-an-email", "password": "pass"})
    assert response.status_code == 422
    data = response.get_json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_me_unauthorized(client):
    """GET /api/auth/me without token should return 401 UNAUTHORIZED."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_me_with_token(client):
    """GET /api/auth/me with valid Bearer token should return user profile."""
    email = os.getenv("VOLUNTEER_EMAIL", "volunteer@ngo.org")
    password = os.getenv("VOLUNTEER_PASSWORD", "change-me-volunteer-password")

    login_res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    token = login_res.get_json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["email"] == email
    assert data["role"] == "volunteer"
