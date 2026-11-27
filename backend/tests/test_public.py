"""Automated tests for QR code PNG generation and public dog endpoint (Step B8)."""

from datetime import date, timedelta
from io import BytesIO
import os

from PIL import Image

from app.extensions import db
from app.models.area import Area
from app.models.audit_log import AuditLog
from app.models.case import Case
from app.models.dog import Dog
from app.models.dog_photo import DogPhoto
from app.models.vaccination import Vaccination
from app.services.storage import resolve_upload_dir


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


def test_qr_png_and_public_dog_endpoint(app, client):
    """Verify QR PNG generation, strict public allow-list, and 404 on invalid/deleted dogs."""
    app.config["STORAGE_BACKEND"] = "local"
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
    photo_id = None
    storage_key = None

    try:
        # 1. Create a dog WITH sensitive guardian, medical, and GPS details
        dog_res = client.post(
            "/api/dogs",
            json={
                "area_id": area_id,
                "sex": "female",
                "guardian_name": "Secret Guardian",
                "guardian_phone": "+91-99999-88888",
                "capture_address": "Secret Street 42",
                "landmark": "Secret Landmark",
                "latitude": 19.076,
                "longitude": 72.8777,
                "medical_conditions": "Sensitive Medical Condition",
                "medical_history": "Sensitive Medical History",
            },
            headers=vol_headers,
        )
        assert dog_res.status_code == 201
        dog_data = dog_res.get_json()
        dog_id = dog_data["id"]
        public_token = dog_data["public_token"]
        dog_code = dog_data["dog_code"]

        # 2. Failure: QR endpoint requires login (401)
        unauth_qr = client.get(f"/api/dogs/{dog_id}/qr.png")
        assert unauth_qr.status_code == 401
        assert unauth_qr.get_json()["error"]["code"] == "UNAUTHORIZED"

        # 3. Success: Staff downloads QR PNG
        qr_res = client.get(f"/api/dogs/{dog_id}/qr.png", headers=vol_headers)
        assert qr_res.status_code == 200
        assert qr_res.mimetype == "image/png"
        assert f'filename="{dog_code}.png"' in qr_res.headers.get("Content-Disposition", "")
        with Image.open(BytesIO(qr_res.data)) as qr_img:
            assert qr_img.format == "PNG"

        # 4. Upload primary photo, add surgery case, and add 2 vaccinations
        img = Image.new("RGB", (300, 300), color=(80, 140, 200))
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        up_res = client.post(
            f"/api/dogs/{dog_id}/photos",
            data={"file": (buf, "public_test.png"), "is_primary": "true"},
            content_type="multipart/form-data",
            headers=vol_headers,
        )
        assert up_res.status_code == 201
        photo_id = up_res.get_json()["id"]
        storage_key = up_res.get_json()["storage_key"]

        today = date.today()
        case_res = client.post(
            f"/api/dogs/{dog_id}/cases",
            json={
                "pickup_date": (today - timedelta(days=2)).isoformat(),
                "surgery_date": (today - timedelta(days=1)).isoformat(),
                "pre_op_notes": "Secret pre-op notes",
            },
            headers=vol_headers,
        )
        assert case_res.status_code == 201
        case_id = case_res.get_json()["id"]

        vax1 = client.post(
            f"/api/dogs/{dog_id}/vaccinations",
            json={"vaccine_name": "7-in-1", "date_given": (today - timedelta(days=10)).isoformat()},
            headers=vol_headers,
        )
        assert vax1.status_code == 201
        vax_ids.append(vax1.get_json()["id"])

        vax2 = client.post(
            f"/api/dogs/{dog_id}/vaccinations",
            json={"vaccine_name": "Anti-Rabies", "date_given": today.isoformat()},
            headers=vol_headers,
        )
        assert vax2.status_code == 201
        vax_ids.append(vax2.get_json()["id"])

        # 5. Success: Unauthenticated public endpoint returns ONLY allow-listed fields
        pub_res = client.get(f"/api/public/dogs/{public_token}")
        assert pub_res.status_code == 200
        pub_data = pub_res.get_json()

        expected_keys = {
            "dog_code",
            "area_name",
            "area_color_name",
            "area_color_hex",
            "primary_photo_url",
            "sterilized",
            "latest_vaccination",
            "ngo_contact",
        }
        assert set(pub_data.keys()) == expected_keys
        assert pub_data["dog_code"] == dog_code
        assert pub_data["area_name"] == "Central Zone - Ward 1"
        assert pub_data["area_color_hex"] == "#0D9488"
        assert f"/media/{storage_key}" in pub_data["primary_photo_url"]
        assert pub_data["sterilized"] is True
        assert pub_data["latest_vaccination"] == {
            "vaccine_name": "Anti-Rabies",
            "date_given": today.isoformat(),
        }
        assert pub_data["ngo_contact"]

        # Verify zero sensitive info leaked anywhere in JSON
        serialized = str(pub_data)
        for secret in (
            "Secret Guardian",
            "99999",
            "Secret Street",
            "Secret Landmark",
            "19.076",
            "72.8777",
            "Sensitive Medical",
            "Secret pre-op",
        ):
            assert secret not in serialized

        # 6. Failure: Unknown token -> 404
        bad_pub = client.get("/api/public/dogs/non-existent-token-xyz")
        assert bad_pub.status_code == 404
        assert bad_pub.get_json()["error"]["code"] == "NOT_FOUND"

        # 7. Failure: Soft-deleted dog -> 404 on both public and qr.png
        del_res = client.delete(f"/api/dogs/{dog_id}", headers=adm_headers)
        assert del_res.status_code == 200
        assert client.get(f"/api/public/dogs/{public_token}").status_code == 404
        assert client.get(f"/api/dogs/{dog_id}/qr.png", headers=adm_headers).status_code == 404
    finally:
        with app.app_context():
            if storage_key:
                file_path = (resolve_upload_dir() / storage_key).resolve()
                if file_path.is_file():
                    file_path.unlink()
            if photo_id:
                AuditLog.query.filter_by(table_name="dog_photos", record_id=photo_id).delete()
                p_obj = db.session.get(DogPhoto, photo_id)
                if p_obj:
                    db.session.delete(p_obj)
            for vid in vax_ids:
                AuditLog.query.filter_by(table_name="vaccinations", record_id=vid).delete()
                v_obj = db.session.get(Vaccination, vid)
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
