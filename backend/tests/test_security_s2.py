"""Tests for SEC-06 through SEC-10 security hardening controls."""

from io import BytesIO
import logging
from PIL import Image

from app.models.audit_log import AuditLog


def _make_png_bytes(width: int = 20, height: int = 20) -> bytes:
    """Create a valid in-memory PNG image."""
    img = Image.new("RGB", (width, height), color=(10, 120, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_dog(client, headers, area_id: int, landmark: str = "Main Gate") -> int:
    """Helper to register a dog and return its ID."""
    res = client.post(
        "/api/dogs",
        headers=headers,
        json={
            "area_id": area_id,
            "sex": "female",
            "approx_age": "2 years",
            "age_group": "adult",
            "coat_description": "Brown and white",
            "landmark": landmark,
        },
    )
    assert res.status_code == 201
    return res.get_json()["id"]


def test_security_headers_api_and_media(client, admin_headers, sample_area):
    """SEC-06: API responses get security headers + no-store; /media/* gets cacheable header."""
    api_res = client.get("/api/health")
    assert api_res.status_code == 200
    assert api_res.headers.get("X-Content-Type-Options") == "nosniff"
    assert api_res.headers.get("X-Frame-Options") == "DENY"
    assert api_res.headers.get("Referrer-Policy") == "no-referrer"
    assert api_res.headers.get("Permissions-Policy") == "geolocation=(), microphone=(), camera=()"
    assert api_res.headers.get("Cache-Control") == "no-store"

    dog_id = _create_dog(client, admin_headers, sample_area.id)
    upload_res = client.post(
        f"/api/dogs/{dog_id}/photos",
        headers=admin_headers,
        data={"file": (BytesIO(_make_png_bytes()), "dog.png")},
        content_type="multipart/form-data",
    )
    assert upload_res.status_code == 201
    photo_url = upload_res.get_json()["url"]

    media_res = client.get(photo_url)
    assert media_res.status_code == 200
    assert media_res.headers.get("X-Content-Type-Options") == "nosniff"
    assert "no-store" not in (media_res.headers.get("Cache-Control") or "")
    assert "max-age=" in (media_res.headers.get("Cache-Control") or "")


def test_export_audit_logging(app, client, admin_headers, sample_area):
    """SEC-07: Excel and Analytics exports write action='export' audit logs without PII."""
    _create_dog(client, admin_headers, sample_area.id, landmark="Near Temple")

    xlsx_res = client.get("/api/export/excel", headers=admin_headers)
    assert xlsx_res.status_code == 200

    analytics_res = client.get(
        "/api/analytics/export?format=json&include_personal=true",
        headers=admin_headers,
    )
    assert analytics_res.status_code == 200

    with app.app_context():
        logs = (
            AuditLog.query.filter_by(action="export")
            .order_by(AuditLog.id.asc())
            .all()
        )
        assert len(logs) == 2
        assert logs[0].table_name == "export_excel"
        assert logs[0].changes["format"] == "xlsx"
        assert logs[0].changes["row_count"] >= 1
        assert logs[1].table_name == "analytics_export"
        assert logs[1].changes["format"] == "json"
        assert logs[1].changes["include_personal"] is True
        assert logs[1].changes["row_count"] >= 1


def test_like_wildcard_escaping_in_dog_search(client, admin_headers, sample_area):
    """SEC-08: Literal % and _ in ?search= do not act as SQL wildcards."""
    _create_dog(client, admin_headers, sample_area.id, landmark="100% Pure Spot")
    _create_dog(client, admin_headers, sample_area.id, landmark="Sector_A Gate")
    _create_dog(client, admin_headers, sample_area.id, landmark="Plain Park")

    pct_res = client.get("/api/dogs?search=%25", headers=admin_headers)
    assert pct_res.status_code == 200
    pct_items = pct_res.get_json()["items"]
    assert len(pct_items) == 1
    assert pct_items[0]["landmark"] == "100% Pure Spot"

    underscore_res = client.get("/api/dogs?search=_", headers=admin_headers)
    assert underscore_res.status_code == 200
    underscore_items = underscore_res.get_json()["items"]
    assert len(underscore_items) == 1
    assert underscore_items[0]["landmark"] == "Sector_A Gate"


def test_image_pixel_limit_and_photo_cap(app, client, admin_headers, sample_area):
    """SEC-09: Decompression bomb returns 422; exceeding MAX_PHOTOS_PER_DOG returns 409."""
    dog_id = _create_dog(client, admin_headers, sample_area.id)

    app.config["MAX_IMAGE_PIXELS"] = 100
    big_res = client.post(
        f"/api/dogs/{dog_id}/photos",
        headers=admin_headers,
        data={"file": (BytesIO(_make_png_bytes(20, 20)), "big.png")},
        content_type="multipart/form-data",
    )
    assert big_res.status_code == 422
    assert big_res.get_json()["error"]["code"] == "IMAGE_TOO_LARGE_DIMENSIONS"

    app.config["MAX_IMAGE_PIXELS"] = 20_000_000
    app.config["MAX_PHOTOS_PER_DOG"] = 2

    for idx in range(2):
        ok_res = client.post(
            f"/api/dogs/{dog_id}/photos",
            headers=admin_headers,
            data={"file": (BytesIO(_make_png_bytes()), f"ok{idx}.png")},
            content_type="multipart/form-data",
        )
        assert ok_res.status_code == 201

    cap_res = client.post(
        f"/api/dogs/{dog_id}/photos",
        headers=admin_headers,
        data={"file": (BytesIO(_make_png_bytes()), "third.png")},
        content_type="multipart/form-data",
    )
    assert cap_res.status_code == 409
    assert cap_res.get_json()["error"]["code"] == "PHOTO_LIMIT_REACHED"


def test_failed_login_logging_and_safe_500(app, client, caplog):
    """SEC-10: Failed login logs warning without password; unhandled exception returns safe 500 JSON."""
    @app.get("/api/test-boom")
    def _boom():
        raise RuntimeError("sensitive internal detail")

    secret_pw = "SuperSecretWrongPass123!"
    with caplog.at_level(logging.WARNING):
        login_res = client.post(
            "/api/auth/login",
            json={"email": "admin@ngo.org", "password": secret_pw},
        )
    assert login_res.status_code == 401
    assert "X-Request-ID" in login_res.headers
    assert any("Failed login attempt" in r.message for r in caplog.records)
    assert all(secret_pw not in r.message for r in caplog.records)

    app.config["PROPAGATE_EXCEPTIONS"] = False
    boom_res = client.get("/api/test-boom")
    assert boom_res.status_code == 500
    body = boom_res.get_json()
    assert body == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
        }
    }
    assert "sensitive internal detail" not in boom_res.get_data(as_text=True)
