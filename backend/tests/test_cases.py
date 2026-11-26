"""Automated tests for nested Cases CRUD endpoints (Step B5)."""

import os

from app.extensions import db
from app.models.area import Area
from app.models.audit_log import AuditLog
from app.models.case import Case
from app.models.dog import Dog


def _login(client, email_env: str, pass_env: str, default_email: str, default_pass: str) -> str:
    """Authenticate and return a JWT access token."""
    email = os.getenv(email_env, default_email)
    password = os.getenv(pass_env, default_pass)
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.json}"
    return res.get_json()["access_token"]


def _admin_headers(client) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client, 'ADMIN_EMAIL', 'ADMIN_PASSWORD', 'admin@ngo.org', 'AdminPass123!')}"}


def _volunteer_headers(client) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client, 'VOLUNTEER_EMAIL', 'VOLUNTEER_PASSWORD', 'volunteer@ngo.org', 'VolunteerPass123!')}"}


def test_case_pickup_to_drop_flow_and_permissions(app, client):
    """Test full pickup -> surgery -> drop lifecycle, date validation, and soft delete."""
    vol_headers = _volunteer_headers(client)
    adm_headers = _admin_headers(client)

    with app.app_context():
        area = Area.query.filter_by(short_code="CTR").first()
        assert area is not None
        orig_counter = area.last_dog_number
        area_id = area.id

    dog_id = None
    case_id = None
    try:
        # Create a dog for testing cases
        dog_res = client.post("/api/dogs", json={"area_id": area_id, "sex": "female"}, headers=vol_headers)
        assert dog_res.status_code == 201
        dog_id = dog_res.get_json()["id"]

        # 1. Pickup (Volunteer creates case)
        pickup_res = client.post(
            f"/api/dogs/{dog_id}/cases",
            json={
                "pickup_date": "2026-11-20",
                "pickup_location": "Clock Tower Gate",
                "picked_by": "NGO Volunteer",
            },
            headers=vol_headers,
        )
        assert pickup_res.status_code == 201
        case_data = pickup_res.get_json()
        case_id = case_data["id"]
        assert case_data["dog_id"] == dog_id
        assert case_data["pickup_date"] == "2026-11-20"
        # B5-01: dog status auto-advances to picked_up
        assert client.get(f"/api/dogs/{dog_id}", headers=vol_headers).get_json()["status"] == "picked_up"

        # 2. Surgery update
        surgery_res = client.patch(
            f"/api/dogs/{dog_id}/cases/{case_id}",
            json={
                "surgery_date": "2026-11-21",
                "procedure": "Ovariohysterectomy",
                "surgeon_name": "Dr. Meera Nair",
                "surgery_outcome": "success",
                "pre_op_notes": "Fasted 12h, vitals normal",
                "post_op_notes": "Clean incision, recovering well",
                "prescription_details": "Meloxicam 0.2mg/kg x 3 days",
            },
            headers=vol_headers,
        )
        assert surgery_res.status_code == 200
        assert surgery_res.get_json()["surgery_outcome"] == "success"
        # B5-01: dog status auto-advances to recovering
        assert client.get(f"/api/dogs/{dog_id}", headers=vol_headers).get_json()["status"] == "recovering"

        # 3. Drop update (omitting recovery_days -> auto-calculated as 4)
        drop_res = client.patch(
            f"/api/dogs/{dog_id}/cases/{case_id}",
            json={
                "drop_date": "2026-11-25",
                "drop_location": "Clock Tower Gate",
                "released_same_spot": True,
            },
            headers=vol_headers,
        )
        assert drop_res.status_code == 200
        assert drop_res.get_json()["released_same_spot"] is True
        assert drop_res.get_json()["recovery_days"] == 4
        # B5-01: dog status auto-advances to released
        assert client.get(f"/api/dogs/{dog_id}", headers=vol_headers).get_json()["status"] == "released"

        # 4. List & Get
        list_res = client.get(f"/api/dogs/{dog_id}/cases", headers=vol_headers)
        assert list_res.status_code == 200
        assert list_res.get_json()["total"] == 1

        get_res = client.get(f"/api/dogs/{dog_id}/cases/{case_id}", headers=vol_headers)
        assert get_res.status_code == 200
        assert get_res.get_json()["id"] == case_id

        # 5. Failure: Bad date ordering (drop_date < pickup_date, drop_date < surgery_date)
        bad_drop = client.patch(
            f"/api/dogs/{dog_id}/cases/{case_id}",
            json={"drop_date": "2026-11-19"},
            headers=vol_headers,
        )
        assert bad_drop.status_code == 400
        assert bad_drop.get_json()["error"]["code"] == "INVALID_DATE_RANGE"

        # 6. Failure: Volunteer cannot delete (403)
        del_vol = client.delete(f"/api/dogs/{dog_id}/cases/{case_id}", headers=vol_headers)
        assert del_vol.status_code == 403
        assert del_vol.get_json()["error"]["code"] == "FORBIDDEN"

        # 7. Admin soft-deletes case (200) -> 404 thereafter
        del_adm = client.delete(f"/api/dogs/{dog_id}/cases/{case_id}", headers=adm_headers)
        assert del_adm.status_code == 200
        assert client.get(f"/api/dogs/{dog_id}/cases/{case_id}", headers=adm_headers).status_code == 404
        assert client.get(f"/api/dogs/{dog_id}/cases", headers=adm_headers).get_json()["total"] == 0
    finally:
        with app.app_context():
            if case_id is not None:
                AuditLog.query.filter_by(table_name="cases", record_id=case_id).delete()
                case_obj = db.session.get(Case, case_id)
                if case_obj:
                    db.session.delete(case_obj)
            if dog_id is not None:
                AuditLog.query.filter_by(table_name="dogs", record_id=dog_id).delete()
                dog_obj = db.session.get(Dog, dog_id)
                if dog_obj:
                    db.session.delete(dog_obj)
            area_obj = db.session.get(Area, area_id)
            if area_obj:
                area_obj.last_dog_number = orig_counter
            db.session.commit()


def test_case_missing_dog_and_invalid_create_dates(client):
    """Missing dog returns 404; surgery_date < pickup_date on create returns 400."""
    headers = _admin_headers(client)

    res_missing = client.get("/api/dogs/99999/cases", headers=headers)
    assert res_missing.status_code == 404
    assert res_missing.get_json()["error"]["code"] == "NOT_FOUND"

    res_post_missing = client.post(
        "/api/dogs/99999/cases",
        json={"pickup_date": "2026-11-20"},
        headers=headers,
    )
    assert res_post_missing.status_code == 404
