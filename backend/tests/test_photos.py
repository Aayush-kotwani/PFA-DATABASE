"""Automated tests for Dog Photos CRUD, WebP processing, and LocalStorage (Step B7)."""

from io import BytesIO
import os

from PIL import Image

from app.extensions import db
from app.models.area import Area
from app.models.audit_log import AuditLog
from app.models.dog import Dog
from app.models.dog_photo import DogPhoto
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


def _make_jpeg_with_exif(width: int = 2000, height: int = 1000) -> BytesIO:
    """Create an in-memory JPEG with Orientation=6 (90° CW) and camera Make EXIF tags."""
    img = Image.new("RGB", (width, height), color=(200, 120, 60))
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: Rotate 90 CW (will become 1000x2000 after transpose)
    exif[0x010F] = "TestPhoneCamera"  # Make tag that must be stripped
    buf = BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    buf.seek(0)
    return buf


def _make_png(width: int = 400, height: int = 300) -> BytesIO:
    """Create a small in-memory PNG image."""
    img = Image.new("RGBA", (width, height), color=(50, 150, 220, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_photo_upload_processing_primary_and_soft_delete(app, client):
    """Test EXIF fix/strip, resize <=1200px, WebP conversion, /media serving, primary toggle, and soft delete."""
    app.config["STORAGE_BACKEND"] = "local"
    vol_headers = _volunteer_headers(client)
    adm_headers = _admin_headers(client)

    with app.app_context():
        area = Area.query.filter_by(short_code="CTR").first()
        assert area is not None
        orig_counter = area.last_dog_number
        area_id = area.id

    dog_id = None
    photo_ids: list[int] = []
    storage_keys: list[str] = []

    try:
        dog_res = client.post("/api/dogs", json={"area_id": area_id, "sex": "female"}, headers=vol_headers)
        assert dog_res.status_code == 201
        dog_id = dog_res.get_json()["id"]

        # 1. Upload JPEG with EXIF rotation & camera metadata
        up1 = client.post(
            f"/api/dogs/{dog_id}/photos",
            data={
                "file": (_make_jpeg_with_exif(2000, 1000), "phone_photo.jpg"),
                "photo_type": "intake",
            },
            content_type="multipart/form-data",
            headers=vol_headers,
        )
        assert up1.status_code == 201
        p1 = up1.get_json()
        photo_ids.append(p1["id"])
        storage_keys.append(p1["storage_key"])
        assert p1["storage_key"].endswith(".webp")
        assert p1["is_primary"] is True
        assert f"/media/{p1['storage_key']}" in p1["url"]

        # Serve via /media/<key> and verify WebP, dimensions (600x1200 after EXIF transpose + resize), and stripped EXIF
        with client.get(f"/media/{p1['storage_key']}") as media_res:
            assert media_res.status_code == 200
            with Image.open(BytesIO(media_res.data)) as stored_img:
                assert stored_img.format == "WEBP"
                assert stored_img.size == (600, 1200)
                assert max(stored_img.size) <= 1200
                assert len(stored_img.getexif()) == 0

        # 2. Upload second PNG photo -> is_primary defaults to False
        up2 = client.post(
            f"/api/dogs/{dog_id}/photos",
            data={
                "file": (_make_png(), "recovery.png"),
                "photo_type": "post_surgery",
            },
            content_type="multipart/form-data",
            headers=vol_headers,
        )
        assert up2.status_code == 201
        p2 = up2.get_json()
        photo_ids.append(p2["id"])
        storage_keys.append(p2["storage_key"])
        assert p2["is_primary"] is False

        # 3. Set second photo as primary -> only second photo has is_primary=True
        patch_res = client.patch(
            f"/api/dogs/{dog_id}/photos/{p2['id']}",
            json={"is_primary": True},
            headers=vol_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.get_json()["is_primary"] is True

        list_res = client.get(f"/api/dogs/{dog_id}/photos", headers=vol_headers)
        assert list_res.status_code == 200
        items = list_res.get_json()["items"]
        assert len(items) == 2
        primary_ids = [item["id"] for item in items if item["is_primary"]]
        assert primary_ids == [p2["id"]]

        # 4. Failure: invalid non-image file
        bad_up = client.post(
            f"/api/dogs/{dog_id}/photos",
            data={"file": (BytesIO(b"not an image"), "fake.jpg")},
            content_type="multipart/form-data",
            headers=vol_headers,
        )
        assert bad_up.status_code == 400
        assert bad_up.get_json()["error"]["code"] == "INVALID_IMAGE"

        # 5. Failure: volunteer delete blocked (403)
        del_vol = client.delete(f"/api/dogs/{dog_id}/photos/{p1['id']}", headers=vol_headers)
        assert del_vol.status_code == 403
        assert del_vol.get_json()["error"]["code"] == "FORBIDDEN"

        # 6. Admin soft delete -> removed from list
        del_adm = client.delete(f"/api/dogs/{dog_id}/photos/{p1['id']}", headers=adm_headers)
        assert del_adm.status_code == 200
        list_after = client.get(f"/api/dogs/{dog_id}/photos", headers=adm_headers).get_json()["items"]
        assert [item["id"] for item in list_after] == [p2["id"]]
    finally:
        with app.app_context():
            upload_dir = resolve_upload_dir()
            for key in storage_keys:
                file_path = (upload_dir / key).resolve()
                if file_path.is_file():
                    file_path.unlink()
            for pid in photo_ids:
                AuditLog.query.filter_by(table_name="dog_photos", record_id=pid).delete()
                p_obj = db.session.get(DogPhoto, pid)
                if p_obj:
                    db.session.delete(p_obj)
            if dog_id is not None:
                AuditLog.query.filter_by(table_name="dogs", record_id=dog_id).delete()
                d_obj = db.session.get(Dog, dog_id)
                if d_obj:
                    db.session.delete(d_obj)
            area_obj = db.session.get(Area, area_id)
            if area_obj:
                area_obj.last_dog_number = orig_counter
            db.session.commit()
