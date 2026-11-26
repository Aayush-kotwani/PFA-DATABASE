"""Automated tests for Vaccinations CRUD and due-date tracking (Step B6)."""

from datetime import date, timedelta
import os

from app.extensions import db
from app.models.area import Area
from app.models.audit_log import AuditLog
from app.models.case import Case
from app.models.dog import Dog
from app.models.vaccination import Vaccination


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


def test_vaccination_lifecycle_and_due_endpoint(app, client):
    """Test create, list, update, /due grouping, validation errors, and soft delete."""
    vol_headers = _volunteer_headers(client)
    adm_headers = _admin_headers(client)

    with app.app_context():
        area = Area.query.filter_by(short_code="CTR").first()
        assert area is not None
        orig_counter = area.last_dog_number
        area_id = area.id

    dog_id = None
    case_id = None
    vax_ids: list[int] = []
    today = date.today()

    try:
        # Create test dog and linked case
        dog_res = client.post("/api/dogs", json={"area_id": area_id, "sex": "male"}, headers=vol_headers)
        assert dog_res.status_code == 201
        dog_data = dog_res.get_json()
        dog_id = dog_data["id"]

        case_res = client.post(
            f"/api/dogs/{dog_id}/cases",
            json={"pickup_date": today.isoformat()},
            headers=vol_headers,
        )
        assert case_res.status_code == 201
        case_id = case_res.get_json()["id"]

        # 1. Create overdue vaccination (next_due_date 5 days ago)
        overdue_due = (today - timedelta(days=5)).isoformat()
        overdue_given = (today - timedelta(days=35)).isoformat()
        res1 = client.post(
            f"/api/dogs/{dog_id}/vaccinations",
            json={
                "vaccine_name": "Anti-Rabies",
                "date_given": overdue_given,
                "next_due_date": overdue_due,
                "case_id": case_id,
                "batch_no": "ARV-01",
                "given_by": "Dr. Rao",
            },
            headers=vol_headers,
        )
        assert res1.status_code == 201
        vax1_id = res1.get_json()["id"]
        vax_ids.append(vax1_id)

        # 2. Create upcoming vaccination (next_due_date 10 days from today)
        upcoming_due = (today + timedelta(days=10)).isoformat()
        res2 = client.post(
            f"/api/dogs/{dog_id}/vaccinations",
            json={
                "vaccine_name": "7-in-1 Booster",
                "date_given": today.isoformat(),
                "next_due_date": upcoming_due,
                "given_by": "Dr. Rao",
            },
            headers=vol_headers,
        )
        assert res2.status_code == 201
        vax2_id = res2.get_json()["id"]
        vax_ids.append(vax2_id)

        # 3. List & Get
        list_res = client.get(f"/api/dogs/{dog_id}/vaccinations", headers=vol_headers)
        assert list_res.status_code == 200
        assert list_res.get_json()["total"] == 2

        get_res = client.get(f"/api/dogs/{dog_id}/vaccinations/{vax1_id}", headers=vol_headers)
        assert get_res.status_code == 200
        assert get_res.get_json()["vaccine_name"] == "Anti-Rabies"

        # 4. Due endpoint check
        due_res = client.get("/api/vaccinations/due?days=30", headers=vol_headers)
        assert due_res.status_code == 200
        due_data = due_res.get_json()
        overdue_ids = [item["id"] for item in due_data["overdue"]]
        upcoming_ids = [item["id"] for item in due_data["upcoming"]]
        assert vax1_id in overdue_ids
        assert vax2_id in upcoming_ids

        vax1_item = next(item for item in due_data["overdue"] if item["id"] == vax1_id)
        assert vax1_item["days_until_due"] == -5
        assert vax1_item["dog_code"] == dog_data["dog_code"]
        assert vax1_item["area_name"] == "Central Zone - Ward 1"

        vax2_item = next(item for item in due_data["upcoming"] if item["id"] == vax2_id)
        assert vax2_item["days_until_due"] == 10

        # 5. Update vaccination
        upd_res = client.patch(
            f"/api/dogs/{dog_id}/vaccinations/{vax2_id}",
            json={"notes": "Booster scheduled"},
            headers=vol_headers,
        )
        assert upd_res.status_code == 200
        assert upd_res.get_json()["notes"] == "Booster scheduled"

        # 6. Failure: Bad date order
        bad_date_res = client.post(
            f"/api/dogs/{dog_id}/vaccinations",
            json={
                "vaccine_name": "Invalid Date Vax",
                "date_given": today.isoformat(),
                "next_due_date": (today - timedelta(days=1)).isoformat(),
            },
            headers=vol_headers,
        )
        assert bad_date_res.status_code == 400
        assert bad_date_res.get_json()["error"]["code"] == "INVALID_DATE_RANGE"

        # 7. Failure: Wrong/missing case_id
        bad_case_res = client.post(
            f"/api/dogs/{dog_id}/vaccinations",
            json={
                "vaccine_name": "Bad Case Vax",
                "date_given": today.isoformat(),
                "case_id": 99999,
            },
            headers=vol_headers,
        )
        assert bad_case_res.status_code == 400
        assert bad_case_res.get_json()["error"]["code"] == "INVALID_CASE"

        # 8. Failure: Volunteer delete blocked (403)
        del_vol = client.delete(f"/api/dogs/{dog_id}/vaccinations/{vax1_id}", headers=vol_headers)
        assert del_vol.status_code == 403
        assert del_vol.get_json()["error"]["code"] == "FORBIDDEN"

        # 9. Admin soft delete -> excluded from list and /due
        del_adm = client.delete(f"/api/dogs/{dog_id}/vaccinations/{vax1_id}", headers=adm_headers)
        assert del_adm.status_code == 200
        assert client.get(f"/api/dogs/{dog_id}/vaccinations/{vax1_id}", headers=adm_headers).status_code == 404
        assert client.get(f"/api/dogs/{dog_id}/vaccinations", headers=adm_headers).get_json()["total"] == 1
        due_after = client.get("/api/vaccinations/due?days=30", headers=adm_headers).get_json()
        assert vax1_id not in [item["id"] for item in due_after["overdue"]]
    finally:
        with app.app_context():
            for vid in vax_ids:
                AuditLog.query.filter_by(table_name="vaccinations", record_id=vid).delete()
                v_obj = db.session.get(Vaccination, vid)
                if v_obj:
                    db.session.delete(v_obj)
            if case_id is not None:
                AuditLog.query.filter_by(table_name="cases", record_id=case_id).delete()
                c_obj = db.session.get(Case, case_id)
                if c_obj:
                    db.session.delete(c_obj)
            if dog_id is not None:
                AuditLog.query.filter_by(table_name="dogs", record_id=dog_id).delete()
                d_obj = db.session.get(Dog, dog_id)
                if d_obj:
                    db.session.delete(d_obj)
            area_obj = db.session.get(Area, area_id)
            if area_obj:
                area_obj.last_dog_number = orig_counter
            db.session.commit()
