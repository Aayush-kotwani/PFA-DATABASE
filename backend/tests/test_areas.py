"""Automated tests for Area management endpoints (Step B3)."""

import os
from app.extensions import db
from app.models.area import Area
from app.models.audit_log import AuditLog


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


def test_volunteer_can_read_areas(client):
    """Volunteers are authorized to list areas and read individual area details."""
    vol_token = _get_volunteer_token(client)
    headers = {"Authorization": f"Bearer {vol_token}"}

    # 1. List areas
    res_list = client.get("/api/areas", headers=headers)
    assert res_list.status_code == 200
    data = res_list.get_json()
    assert "items" in data
    assert data["total"] >= 3

    # 2. Get specific area by ID
    res_get = client.get("/api/areas/1", headers=headers)
    assert res_get.status_code == 200
    area = res_get.get_json()
    assert area["id"] == 1
    assert "name" in area
    assert "color_hex" in area
    assert "short_code" in area


def test_volunteer_write_blocked(client):
    """Volunteers must be rejected with 403 FORBIDDEN on all mutation endpoints."""
    vol_token = _get_volunteer_token(client)
    headers = {"Authorization": f"Bearer {vol_token}"}

    # POST /api/areas
    create_res = client.post(
        "/api/areas",
        json={
            "name": "Unauthorized Area",
            "short_code": "UNAUTH",
            "ward_no": "Ward 99",
            "color_name": "Pink",
            "color_hex": "#EC4899",
        },
        headers=headers,
    )
    assert create_res.status_code == 403
    assert create_res.get_json()["error"]["code"] == "FORBIDDEN"

    # PATCH /api/areas/1
    patch_res = client.patch(
        "/api/areas/1",
        json={"name": "Hacked Area"},
        headers=headers,
    )
    assert patch_res.status_code == 403
    assert patch_res.get_json()["error"]["code"] == "FORBIDDEN"

    # POST /api/areas/1/deactivate
    deact_res = client.post("/api/areas/1/deactivate", headers=headers)
    assert deact_res.status_code == 403
    assert deact_res.get_json()["error"]["code"] == "FORBIDDEN"


def test_admin_area_crud_lifecycle(app, client):
    """Full lifecycle: create area, update details, deactivate, and query inactive filter."""
    admin_token = _get_admin_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Ensure test code is clean
    with app.app_context():
        existing = Area.query.filter_by(short_code="WST").first()
        if existing:
            AuditLog.query.filter_by(table_name="areas", record_id=existing.id).delete()
            db.session.delete(existing)
            db.session.commit()

    # 1. Create area
    payload = {
        "name": "West Suburb - Ward 4",
        "short_code": "wst",  # Lowercase should be auto-uppercased
        "ward_no": "Ward 4",
        "color_name": "Emerald",
        "color_hex": "#10b981",  # Lowercase should be auto-uppercased
        "landmark": "Near West Gate Bus Stop",
        "animal_lover_name": "Deepak Mehta",
        "animal_lover_phone": "+91-98765-43213",
    }
    create_res = client.post("/api/areas", json=payload, headers=headers)
    assert create_res.status_code == 201
    created_area = create_res.get_json()
    assert created_area["short_code"] == "WST"
    assert created_area["color_hex"] == "#10B981"
    assert created_area["is_active"] is True
    area_id = created_area["id"]

    # Verify audit log
    with app.app_context():
        audit = AuditLog.query.filter_by(
            table_name="areas", record_id=area_id, action="create"
        ).first()
        assert audit is not None
        assert audit.changes["short_code"] == "WST"

    # 2. Update area
    patch_res = client.patch(
        f"/api/areas/{area_id}",
        json={"landmark": "Updated Metro Bus Stop", "color_name": "Bright Emerald"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.get_json()["landmark"] == "Updated Metro Bus Stop"
    assert patch_res.get_json()["color_name"] == "Bright Emerald"

    # 3. Deactivate area
    deact_res = client.post(f"/api/areas/{area_id}/deactivate", headers=headers)
    assert deact_res.status_code == 200
    assert deact_res.get_json()["is_active"] is False

    # 4. List inactive areas filter
    list_inactive = client.get("/api/areas?is_active=false", headers=headers)
    assert list_inactive.status_code == 200
    inactive_ids = [item["id"] for item in list_inactive.get_json()["items"]]
    assert area_id in inactive_ids

    # Clean up test area
    with app.app_context():
        AuditLog.query.filter_by(table_name="areas", record_id=area_id).delete()
        area_obj = db.session.get(Area, area_id)
        if area_obj:
            db.session.delete(area_obj)
        db.session.commit()


def test_invalid_color_hex_validation(client):
    """Submitting an invalid hex color code returns 422 VALIDATION_ERROR."""
    admin_token = _get_admin_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    for bad_hex in ["red", "#123", "#GGGGGG", "10B981", "#1234567"]:
        res = client.post(
            "/api/areas",
            json={
                "name": "Bad Color Area",
                "short_code": "BCA",
                "ward_no": "Ward 5",
                "color_name": "Bad Color",
                "color_hex": bad_hex,
            },
            headers=headers,
        )
        assert res.status_code == 422
        assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_area_duplicate_conflicts_409(client):
    """Reusing existing name, short_code, or color_hex returns 409 CONFLICT."""
    admin_token = _get_admin_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Duplicate name (case-insensitive)
    res_name = client.post(
        "/api/areas",
        json={
            "name": "central zone - ward 1",  # Existing is "Central Zone - Ward 1"
            "short_code": "NEW1",
            "ward_no": "Ward 10",
            "color_name": "Unique Color",
            "color_hex": "#AABBCC",
        },
        headers=headers,
    )
    assert res_name.status_code == 409
    assert res_name.get_json()["error"]["code"] == "CONFLICT"
    assert "name" in res_name.get_json()["error"]["message"]

    # 2. Duplicate short_code (case-insensitive)
    res_code = client.post(
        "/api/areas",
        json={
            "name": "Brand New Area Name",
            "short_code": "ctr",  # Existing is "CTR"
            "ward_no": "Ward 10",
            "color_name": "Unique Color",
            "color_hex": "#AABBCC",
        },
        headers=headers,
    )
    assert res_code.status_code == 409
    assert res_code.get_json()["error"]["code"] == "CONFLICT"
    assert "short code" in res_code.get_json()["error"]["message"]

    # 3. Duplicate color_hex (case-insensitive)
    res_hex = client.post(
        "/api/areas",
        json={
            "name": "Brand New Area Name 2",
            "short_code": "NEW2",
            "ward_no": "Ward 10",
            "color_name": "Unique Color",
            "color_hex": "#0d9488",  # Existing is "#0D9488"
        },
        headers=headers,
    )
    assert res_hex.status_code == 409
    assert res_hex.get_json()["error"]["code"] == "CONFLICT"
    assert "color hex" in res_hex.get_json()["error"]["message"]


def test_area_not_found_404(client):
    """Referencing a non-existent area returns 404 NOT_FOUND."""
    admin_token = _get_admin_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    assert client.get("/api/areas/99999", headers=headers).status_code == 404
    assert client.patch("/api/areas/99999", json={"name": "Ghost"}, headers=headers).status_code == 404
    assert client.post("/api/areas/99999/deactivate", headers=headers).status_code == 404
