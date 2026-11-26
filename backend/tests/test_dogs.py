"""Automated tests for Dogs CRUD, role-based phone hiding, and soft delete (Step B4)."""

from datetime import datetime, timezone
import os

from app.extensions import db
from app.models.area import Area
from app.models.audit_log import AuditLog
from app.models.dog import Dog


def _login(client, email_env: str, pass_env: str, default_email: str, default_pass: str) -> str:
    """Authenticate and return a JWT access token."""
    email = os.getenv(email_env, default_email)
    password = os.getenv(pass_env, default_pass)
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.json}"
    return res.get_json()["access_token"]


def _admin_headers(client) -> dict[str, str]:
    token = _login(client, "ADMIN_EMAIL", "ADMIN_PASSWORD", "admin@ngo.org", "AdminPass123!")
    return {"Authorization": f"Bearer {token}"}


def _volunteer_headers(client) -> dict[str, str]:
    token = _login(
        client, "VOLUNTEER_EMAIL", "VOLUNTEER_PASSWORD", "volunteer@ngo.org", "VolunteerPass123!"
    )
    return {"Authorization": f"Bearer {token}"}


def test_dog_lifecycle_and_phone_hiding(app, client):
    """Test create, read, update, phone-hiding for volunteers, and soft delete."""
    vol_headers = _volunteer_headers(client)
    adm_headers = _admin_headers(client)

    with app.app_context():
        area = Area.query.filter_by(short_code="CTR").first()
        assert area is not None
        orig_counter = area.last_dog_number
        area_id = area.id

    dog_id = None
    try:
        # 1. Volunteer creates a dog with ALL fields including guardian_phone
        payload = {
            "area_id": area_id,
            "sex": "female",
            "approx_age": "2 years",
            "age_group": "adult",
            "coat_description": "Brown and white",
            "weight_kg": 14.5,
            "body_condition": "normal",
            "is_pregnant": False,
            "temperament": "Calm",
            "guardian_name": "Ramesh Kumar",
            "guardian_phone": "+91-99999-11111",
            "capture_address": "12 Market Lane",
            "landmark": "Clock Tower Gate",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "ear_notch_done": False,
            "status": "registered",
            "medical_conditions": "Minor tick fever",
            "medical_history": "Dewormed last month",
        }
        create_res = client.post("/api/dogs", json=payload, headers=vol_headers)
        assert create_res.status_code == 201
        dog_data = create_res.get_json()
        dog_id = dog_data["id"]

        # Verify dog_code, area summary, maps_url, rounded GPS, and phone stripped for volunteer
        assert dog_data["dog_code"] == f"CTR-{orig_counter + 1:04d}"
        assert dog_data["area"]["name"] == "Central Zone - Ward 1"
        assert dog_data["area"]["color_hex"] == "#0D9488"
        assert dog_data["latitude"] == 19.076
        assert dog_data["longitude"] == 72.8777
        assert dog_data["maps_url"] == "https://www.google.com/maps?q=19.076000,72.877700"
        assert "guardian_phone" not in dog_data

        # Verify audit_logs for create never stores plaintext guardian_phone
        with app.app_context():
            create_audit = AuditLog.query.filter_by(
                table_name="dogs", record_id=dog_id, action="create"
            ).first()
            assert create_audit is not None
            assert create_audit.changes.get("guardian_phone") == {"provided": True}
            assert "+91-99999-11111" not in str(create_audit.changes)

        # 2. Volunteer GET single & list never expose guardian_phone
        get_vol = client.get(f"/api/dogs/{dog_id}", headers=vol_headers)
        assert get_vol.status_code == 200
        assert "guardian_phone" not in get_vol.get_json()

        list_vol = client.get("/api/dogs", headers=vol_headers)
        assert list_vol.status_code == 200
        for item in list_vol.get_json()["items"]:
            assert "guardian_phone" not in item

        # 3. Volunteer PATCH updates medical_conditions, but guardian_phone is IGNORED
        patch_vol = client.patch(
            f"/api/dogs/{dog_id}",
            json={
                "medical_conditions": "Recovered from tick fever",
                "guardian_phone": "+91-00000-00000",
            },
            headers=vol_headers,
        )
        assert patch_vol.status_code == 200
        assert patch_vol.get_json()["medical_conditions"] == "Recovered from tick fever"
        assert "guardian_phone" not in patch_vol.get_json()

        # 4. Admin sees original guardian_phone (proving volunteer update didn't overwrite it)
        get_adm = client.get(f"/api/dogs/{dog_id}", headers=adm_headers)
        assert get_adm.status_code == 200
        assert get_adm.get_json()["guardian_phone"] == "+91-99999-11111"

        # 5. Admin can update guardian_phone
        patch_adm = client.patch(
            f"/api/dogs/{dog_id}",
            json={"guardian_phone": "+91-88888-22222"},
            headers=adm_headers,
        )
        assert patch_adm.status_code == 200
        assert patch_adm.get_json()["guardian_phone"] == "+91-88888-22222"

        # Verify audit_logs for update never stores plaintext guardian_phone
        with app.app_context():
            update_audit = (
                AuditLog.query.filter_by(table_name="dogs", record_id=dog_id, action="update")
                .order_by(AuditLog.id.desc())
                .first()
            )
            assert update_audit is not None
            assert update_audit.changes.get("guardian_phone") == {"updated": True}
            assert "+91-88888-22222" not in str(update_audit.changes)
            assert "+91-99999-11111" not in str(update_audit.changes)

        # 6. Search and filters
        today_str = datetime.now(timezone.utc).date().isoformat()
        search_res = client.get(
            f"/api/dogs?search=Clock+Tower&area_id={area_id}&sex=female"
            f"&status=registered&created_from={today_str}&created_to={today_str}",
            headers=adm_headers,
        )
        assert search_res.status_code == 200
        found_ids = [item["id"] for item in search_res.get_json()["items"]]
        assert dog_id in found_ids

        # 7. Volunteer cannot delete (403)
        del_vol = client.delete(f"/api/dogs/{dog_id}", headers=vol_headers)
        assert del_vol.status_code == 403
        assert del_vol.get_json()["error"]["code"] == "FORBIDDEN"

        # 8. Admin soft-deletes dog (200) -> 404 thereafter
        del_adm = client.delete(f"/api/dogs/{dog_id}", headers=adm_headers)
        assert del_adm.status_code == 200
        assert client.get(f"/api/dogs/{dog_id}", headers=adm_headers).status_code == 404
        assert client.patch(f"/api/dogs/{dog_id}", json={"status": "lost"}, headers=adm_headers).status_code == 404
        assert client.delete(f"/api/dogs/{dog_id}", headers=adm_headers).status_code == 404

        list_after = client.get("/api/dogs", headers=adm_headers)
        assert dog_id not in [item["id"] for item in list_after.get_json()["items"]]
    finally:
        # Clean up test dog and restore area counter
        with app.app_context():
            if dog_id is not None:
                AuditLog.query.filter_by(table_name="dogs", record_id=dog_id).delete()
                dog_obj = db.session.get(Dog, dog_id)
                if dog_obj:
                    db.session.delete(dog_obj)
            area_obj = db.session.get(Area, area_id)
            if area_obj:
                area_obj.last_dog_number = orig_counter
            db.session.commit()


def test_dog_validation_and_area_errors(app, client):
    """Invalid GPS ranges return 422; inactive or missing area returns 400/404."""
    headers = _admin_headers(client)

    # Invalid latitude (>90)
    res_lat = client.post(
        "/api/dogs",
        json={"area_id": 1, "latitude": 95.0, "longitude": 72.0},
        headers=headers,
    )
    assert res_lat.status_code == 422
    assert res_lat.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Invalid longitude (<-180)
    res_lng = client.post(
        "/api/dogs",
        json={"area_id": 1, "latitude": 19.0, "longitude": -190.0},
        headers=headers,
    )
    assert res_lng.status_code == 422
    assert res_lng.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Non-existent area
    res_missing = client.post("/api/dogs", json={"area_id": 99999}, headers=headers)
    assert res_missing.status_code == 404
    assert res_missing.get_json()["error"]["code"] == "NOT_FOUND"

    # Inactive area
    with app.app_context():
        inactive_area = Area(
            name="Inactive Dog Test Zone",
            short_code="IDZ",
            ward_no="Ward 99",
            color_name="Slate",
            color_hex="#64748B",
            last_dog_number=0,
            is_active=False,
        )
        db.session.add(inactive_area)
        db.session.commit()
        inactive_id = inactive_area.id

    try:
        res_inactive = client.post("/api/dogs", json={"area_id": inactive_id}, headers=headers)
        assert res_inactive.status_code == 400
        assert res_inactive.get_json()["error"]["code"] == "BAD_REQUEST"
    finally:
        with app.app_context():
            area_obj = db.session.get(Area, inactive_id)
            if area_obj:
                db.session.delete(area_obj)
            db.session.commit()
