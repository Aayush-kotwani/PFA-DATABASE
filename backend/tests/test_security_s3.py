"""Tests for SEC-11, SEC-12, SEC-13, and SEC-15 security hardening controls."""

import os
import pytest

from app import create_app
from app.config import TestingConfig
from scripts import seed as seed_script


def _create_dog(client, headers, area_id: int) -> dict:
    """Helper to register a dog and return its JSON payload."""
    res = client.post(
        "/api/dogs",
        headers=headers,
        json={
            "area_id": area_id,
            "sex": "female",
            "approx_age": "2 years",
            "age_group": "adult",
            "coat_description": "Brown and white",
            "landmark": "Near Clock Tower",
        },
    )
    assert res.status_code == 201
    return res.get_json()


def test_enable_swagger_toggle(monkeypatch):
    """SEC-11: Swagger/OpenAPI disabled when ENABLE_SWAGGER=false or in production by default."""
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("ENABLE_SWAGGER", "false")
    disabled_app = create_app(TestingConfig)
    disabled_client = disabled_app.test_client()
    assert disabled_client.get("/docs").status_code == 404
    assert disabled_client.get("/openapi.json").status_code == 404

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("ENABLE_SWAGGER", raising=False)
    prod_default_app = create_app(TestingConfig)
    prod_client = prod_default_app.test_client()
    assert prod_client.get("/docs").status_code == 404
    assert prod_client.get("/openapi.json").status_code == 404

    monkeypatch.setenv("ENABLE_SWAGGER", "true")
    prod_enabled_app = create_app(TestingConfig)
    prod_enabled_client = prod_enabled_app.test_client()
    assert prod_enabled_client.get("/openapi.json").status_code == 200


def test_change_password_and_token_revocation(client):
    """SEC-12: Self-service password change verifies old password and revokes old JWTs."""
    vol_email = os.getenv("VOLUNTEER_EMAIL", "volunteer@ngo.org")
    vol_pass = os.getenv("VOLUNTEER_PASSWORD", "VolunteerPass123!")

    login_res = client.post(
        "/api/auth/login",
        json={"email": vol_email, "password": vol_pass},
    )
    assert login_res.status_code == 200
    old_token = login_res.get_json()["access_token"]
    old_headers = {"Authorization": f"Bearer {old_token}"}

    wrong_res = client.post(
        "/api/auth/change-password",
        headers=old_headers,
        json={"current_password": "WrongPassword99!", "new_password": "NewStrongPassword99!"},
    )
    assert wrong_res.status_code == 401
    assert wrong_res.get_json()["error"]["code"] == "INVALID_CREDENTIALS"

    same_res = client.post(
        "/api/auth/change-password",
        headers=old_headers,
        json={"current_password": vol_pass, "new_password": vol_pass},
    )
    assert same_res.status_code == 400

    ok_res = client.post(
        "/api/auth/change-password",
        headers=old_headers,
        json={"current_password": vol_pass, "new_password": "NewStrongPassword99!"},
    )
    assert ok_res.status_code == 200
    assert ok_res.get_json()["message"] == "Password changed successfully"

    # Old JWT must be immediately rejected via token_version check
    me_old = client.get("/api/auth/me", headers=old_headers)
    assert me_old.status_code == 401

    # New password works for login
    relogin = client.post(
        "/api/auth/login",
        json={"email": vol_email, "password": "NewStrongPassword99!"},
    )
    assert relogin.status_code == 200


def test_rotate_public_token_permissions_and_invalidation(
    client, admin_headers, volunteer_headers, sample_area
):
    """SEC-13: Admin-only token rotation invalidates old QR URL and activates new token."""
    dog = _create_dog(client, admin_headers, sample_area.id)
    dog_id = dog["id"]
    old_token = dog["public_token"]

    assert client.get(f"/api/public/dogs/{old_token}").status_code == 200

    vol_res = client.post(
        f"/api/dogs/{dog_id}/rotate-token",
        headers=volunteer_headers,
    )
    assert vol_res.status_code == 403

    adm_res = client.post(
        f"/api/dogs/{dog_id}/rotate-token",
        headers=admin_headers,
    )
    assert adm_res.status_code == 200
    new_token = adm_res.get_json()["public_token"]
    assert new_token != old_token

    assert client.get(f"/api/public/dogs/{old_token}").status_code == 404
    assert client.get(f"/api/public/dogs/{new_token}").status_code == 200


def test_seed_script_guards(monkeypatch):
    """SEC-15: seed.py refuses to run in production or with placeholder passwords."""
    monkeypatch.setenv("ADMIN_EMAIL", "admin@ngo.org")
    monkeypatch.setenv("VOLUNTEER_EMAIL", "volunteer@ngo.org")
    monkeypatch.setenv("ADMIN_PASSWORD", "StrongRealAdminPass123!")
    monkeypatch.setenv("VOLUNTEER_PASSWORD", "StrongRealVolPass123!")

    monkeypatch.setenv("FLASK_ENV", "production")
    with pytest.raises(RuntimeError, match="production"):
        seed_script._validate_credentials()

    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setenv("ADMIN_PASSWORD", "change-me-admin-password")
    with pytest.raises(RuntimeError, match="placeholder"):
        seed_script._validate_credentials()
