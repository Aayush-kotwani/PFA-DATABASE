"""Automated tests for User management endpoints (Step B2)."""

import os
from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.user import User


def _get_admin_token(client):
    """Helper to authenticate and return an admin JWT access token."""
    email = os.getenv("ADMIN_EMAIL", "admin@ngo.org")
    password = os.getenv("ADMIN_PASSWORD", "AdminPass123!")
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.json}"
    return res.get_json()["access_token"]


def _get_volunteer_token(client):
    """Helper to authenticate and return a volunteer JWT access token."""
    email = os.getenv("VOLUNTEER_EMAIL", "volunteer@ngo.org")
    password = os.getenv("VOLUNTEER_PASSWORD", "VolunteerPass123!")
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.json}"
    return res.get_json()["access_token"]


def test_list_users_as_admin(client):
    """Admin can list all users with pagination."""
    token = _get_admin_token(client)
    res = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.get_json()
    assert "items" in data
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert data["total"] >= 2
    # Verify password_hash is NEVER exposed
    for item in data["items"]:
        assert "password_hash" not in item
        assert "password" not in item


def test_create_update_and_reset_user_flow(app, client):
    """Full lifecycle: create user, update details, deactivate, and reset password."""
    token = _get_admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Ensure clean state in case a previous run left the test user behind
    with app.app_context():
        existing = User.query.filter_by(email="temp_volunteer@ngo.org").first()
        if existing:
            AuditLog.query.filter_by(table_name="users", record_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

    # 1. Create a new volunteer user
    create_payload = {
        "name": "Temporary Volunteer",
        "email": "temp_volunteer@ngo.org",
        "password": "InitialPass123!",
        "role": "volunteer",
        "is_active": True,
    }
    create_res = client.post("/api/users", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    created_user = create_res.get_json()
    assert created_user["email"] == "temp_volunteer@ngo.org"
    assert created_user["role"] == "volunteer"
    assert "password_hash" not in created_user
    user_id = created_user["id"]

    # Verify audit log for creation
    with app.app_context():
        audit_create = AuditLog.query.filter_by(
            table_name="users", record_id=user_id, action="create"
        ).first()
        assert audit_create is not None
        assert audit_create.changes["email"] == "temp_volunteer@ngo.org"
        assert "password" not in audit_create.changes
        assert "password_hash" not in audit_create.changes

    # 2. Update user name and deactivate
    update_res = client.patch(
        f"/api/users/{user_id}",
        json={"name": "Updated Volunteer", "is_active": False},
        headers=headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.get_json()
    assert updated_data["name"] == "Updated Volunteer"
    assert updated_data["is_active"] is False

    # Verify deactivated user cannot log in
    login_attempt = client.post(
        "/api/auth/login",
        json={"email": "temp_volunteer@ngo.org", "password": "InitialPass123!"},
    )
    assert login_attempt.status_code == 403
    assert login_attempt.get_json()["error"]["code"] == "ACCOUNT_INACTIVE"

    # 3. Reset password and reactivate user
    client.patch(f"/api/users/{user_id}", json={"is_active": True}, headers=headers)
    reset_res = client.post(
        f"/api/users/{user_id}/reset-password",
        json={"new_password": "NewSecretPass456!"},
        headers=headers,
    )
    assert reset_res.status_code == 200
    assert reset_res.get_json()["message"] == "Password reset successfully"

    # Verify audit log for password reset contains NO password
    with app.app_context():
        audit_reset = (
            AuditLog.query.filter_by(table_name="users", record_id=user_id, action="update")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert audit_reset is not None
        assert audit_reset.changes == {"password_reset": True}

    # Verify login works with new password
    new_login = client.post(
        "/api/auth/login",
        json={"email": "temp_volunteer@ngo.org", "password": "NewSecretPass456!"},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.get_json()

    # Clean up test user and its audit logs
    with app.app_context():
        AuditLog.query.filter_by(table_name="users", record_id=user_id).delete()
        user_obj = db.session.get(User, user_id)
        if user_obj:
            db.session.delete(user_obj)
        db.session.commit()


def test_volunteer_forbidden_on_all_user_routes(client):
    """Volunteer role must receive 403 FORBIDDEN on all user management endpoints."""
    vol_token = _get_volunteer_token(client)
    headers = {"Authorization": f"Bearer {vol_token}"}

    # GET /api/users
    res_list = client.get("/api/users/", headers=headers)
    assert res_list.status_code == 403
    assert res_list.get_json()["error"]["code"] == "FORBIDDEN"

    # POST /api/users
    res_create = client.post(
        "/api/users/",
        json={"name": "Hacker", "email": "h@ngo.org", "password": "pass12345"},
        headers=headers,
    )
    assert res_create.status_code == 403
    assert res_create.get_json()["error"]["code"] == "FORBIDDEN"

    # PATCH /api/users/1
    res_patch = client.patch("/api/users/1", json={"name": "Hacked"}, headers=headers)
    assert res_patch.status_code == 403
    assert res_patch.get_json()["error"]["code"] == "FORBIDDEN"

    # POST /api/users/1/reset-password
    res_reset = client.post(
        "/api/users/1/reset-password",
        json={"new_password": "newpass12345"},
        headers=headers,
    )
    assert res_reset.status_code == 403
    assert res_reset.get_json()["error"]["code"] == "FORBIDDEN"


def test_duplicate_email_conflict(client):
    """Creating a user with an existing email returns 409 CONFLICT."""
    token = _get_admin_token(client)
    existing_email = os.getenv("ADMIN_EMAIL", "admin@ngo.org")

    res = client.post(
        "/api/users/",
        json={
            "name": "Duplicate Admin",
            "email": existing_email,
            "password": "SecurePassword123!",
            "role": "admin",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "CONFLICT"


def test_user_not_found_404(client):
    """Updating a non-existent user returns 404 NOT_FOUND."""
    token = _get_admin_token(client)
    res = client.patch(
        "/api/users/99999",
        json={"name": "Ghost User"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    assert res.get_json()["error"]["code"] == "NOT_FOUND"


def test_user_create_validation_error(client):
    """Invalid payload (short password, bad email, >128 char password) returns 422 VALIDATION_ERROR."""
    token = _get_admin_token(client)
    res = client.post(
        "/api/users",
        json={
            "name": "",
            "email": "not-an-email",
            "password": "short",
            "role": "superman",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422
    assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Test password exceeding 128 characters
    long_pass_res = client.post(
        "/api/users",
        json={
            "name": "Long Password User",
            "email": "longpass@ngo.org",
            "password": "A" * 130,
            "role": "volunteer",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert long_pass_res.status_code == 422
    assert long_pass_res.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_admin_self_lockout_guard(client):
    """Admin cannot deactivate or demote their own account."""
    token = _get_admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch admin's own id
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    admin_id = me_res.get_json()["id"]

    # 1. Attempt self-deactivation
    deact_res = client.patch(
        f"/api/users/{admin_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert deact_res.status_code == 400
    assert deact_res.get_json()["error"]["code"] == "BAD_REQUEST"
    assert "deactivate or demote" in deact_res.get_json()["error"]["message"]

    # 2. Attempt self-demotion to volunteer
    demote_res = client.patch(
        f"/api/users/{admin_id}",
        json={"role": "volunteer"},
        headers=headers,
    )
    assert demote_res.status_code == 400
    assert demote_res.get_json()["error"]["code"] == "BAD_REQUEST"
    assert "deactivate or demote" in demote_res.get_json()["error"]["message"]
