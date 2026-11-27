"""Automated tests for Dashboard stats, Audit logs, Excel, and Analytics exports (Step B9)."""

import csv
from datetime import date, timedelta
from io import BytesIO, StringIO
import os

from openpyxl import load_workbook

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


def test_dashboard_audit_excel_and_analytics_exports(app, client):
    """Test dashboard stats, role guards, audit logs, Excel workbook, and privacy-first analytics export."""
    vol_headers = _volunteer_headers(client)
    adm_headers = _admin_headers(client)

    with app.app_context():
        area = Area.query.filter_by(short_code="CTR").first()
        assert area is not None
        orig_counter = area.last_dog_number
        area_id = area.id

    dog_id = None
    case_id = None
    vax_id = None
    today = date.today()

    try:
        # Create test dog with guardian_phone, GPS, and analytics fields
        dog_res = client.post(
            "/api/dogs",
            json={
                "area_id": area_id,
                "sex": "female",
                "age_group": "adult",
                "body_condition": "normal",
                "is_pregnant": False,
                "guardian_name": "Priya Nair",
                "guardian_phone": "+91-98111-22334",
                "capture_address": "15 Park Street",
                "latitude": 19.076,
                "longitude": 72.8777,
            },
            headers=vol_headers,
        )
        assert dog_res.status_code == 201
        dog_data = dog_res.get_json()
        dog_id = dog_data["id"]
        dog_code = dog_data["dog_code"]

        # Create case with surgery_date in current month
        case_res = client.post(
            f"/api/dogs/{dog_id}/cases",
            json={
                "pickup_date": today.isoformat(),
                "surgery_date": today.isoformat(),
                "procedure": "Spay",
                "surgery_outcome": "success",
            },
            headers=vol_headers,
        )
        assert case_res.status_code == 201
        case_id = case_res.get_json()["id"]

        # Create upcoming vaccination due in 5 days
        vax_res = client.post(
            f"/api/dogs/{dog_id}/vaccinations",
            json={
                "vaccine_name": "Anti-Rabies",
                "date_given": today.isoformat(),
                "next_due_date": (today + timedelta(days=5)).isoformat(),
                "case_id": case_id,
            },
            headers=vol_headers,
        )
        assert vax_res.status_code == 201
        vax_id = vax_res.get_json()["id"]

        # 1. Dashboard stats (Volunteer & Admin)
        dash_res = client.get("/api/dashboard/stats", headers=vol_headers)
        assert dash_res.status_code == 200
        dash = dash_res.get_json()
        assert dash["total_dogs"] >= 1
        assert "registered" in dash["by_status"]
        assert "recovering" in dash["by_status"]
        assert dash["sterilized_this_month"] >= 1
        assert dash["vaccinations_due"]["upcoming_30_days"] >= 1
        assert any(a["short_code"] == "CTR" and a["count"] >= 1 for a in dash["by_area"])

        # 2. Failure: Volunteer blocked from admin-only endpoints (403)
        assert client.get("/api/audit-logs", headers=vol_headers).status_code == 403
        assert client.get("/api/export/excel", headers=vol_headers).status_code == 403
        assert client.get("/api/analytics/export", headers=vol_headers).status_code == 403

        # 3. Audit logs (Admin)
        audit_res = client.get(
            f"/api/audit-logs?table_name=dogs&action=create&record_id={dog_id}",
            headers=adm_headers,
        )
        assert audit_res.status_code == 200
        audit_items = audit_res.get_json()["items"]
        assert len(audit_items) == 1
        assert audit_items[0]["user_name"] == "NGO Volunteer"
        assert "+91-98111-22334" not in str(audit_items[0]["changes"])

        # 4. Excel export (Admin)
        xlsx_res = client.get("/api/export/excel", headers=adm_headers)
        assert xlsx_res.status_code == 200
        wb = load_workbook(BytesIO(xlsx_res.data))
        assert wb.sheetnames == ["Dogs", "Cases", "Vaccinations"]
        dogs_rows = list(wb["Dogs"].iter_rows(values_only=True))
        assert "Guardian Phone" in dogs_rows[0]
        phone_idx = dogs_rows[0].index("Guardian Phone")
        code_idx = dogs_rows[0].index("Dog Code")
        matching_dog_rows = [r for r in dogs_rows[1:] if r[code_idx] == dog_code]
        assert len(matching_dog_rows) == 1
        assert matching_dog_rows[0][phone_idx] == "+91-98111-22334"

        # 5. Analytics flat export - JSON default (include_personal=False)
        an_json = client.get("/api/analytics/export?format=json", headers=adm_headers)
        assert an_json.status_code == 200
        an_data = an_json.get_json()
        assert an_data["include_personal"] is False
        row = next(item for item in an_data["items"] if item["dog_id"] == dog_id)
        assert row["sterilized"] is True
        assert row["vaccination_count"] == 1
        for pii_field in (
            "guardian_name",
            "guardian_phone",
            "capture_address",
            "latitude",
            "longitude",
            "maps_url",
        ):
            assert pii_field not in row

        # 6. Analytics flat export - CSV default (include_personal=False)
        an_csv = client.get("/api/analytics/export?format=csv", headers=adm_headers)
        assert an_csv.status_code == 200
        assert "text/csv" in an_csv.mimetype
        reader = csv.DictReader(StringIO(an_csv.data.decode("utf-8")))
        assert "guardian_phone" not in (reader.fieldnames or [])
        csv_rows = list(reader)
        assert any(r["dog_code"] == dog_code and r["vaccination_count"] == "1" for r in csv_rows)

        # 7. Analytics flat export - JSON with include_personal=true
        an_priv = client.get(
            "/api/analytics/export?format=json&include_personal=true",
            headers=adm_headers,
        )
        assert an_priv.status_code == 200
        priv_row = next(item for item in an_priv.get_json()["items"] if item["dog_id"] == dog_id)
        assert priv_row["guardian_name"] == "Priya Nair"
        assert priv_row["guardian_phone"] == "+91-98111-22334"
        assert priv_row["latitude"] == 19.076
    finally:
        with app.app_context():
            if vax_id:
                AuditLog.query.filter_by(table_name="vaccinations", record_id=vax_id).delete()
                v_obj = db.session.get(Vaccination, vax_id)
                if v_obj:
                    db.session.delete(v_obj)
            if case_id:
                AuditLog.query.filter_by(table_name="cases", record_id=case_id).delete()
                c_obj = db.session.get(Case, case_id)
                if c_obj:
                    db.session.delete(c_obj)
            if dog_id:
                AuditLog.query.filter_by(table_name="dogs", record_id=dog_id).delete()
                d_obj = db.session.get(Dog, dog_id)
                if d_obj:
                    db.session.delete(d_obj)
            area_obj = db.session.get(Area, area_id)
            if area_obj:
                area_obj.last_dog_number = orig_counter
            db.session.commit()
