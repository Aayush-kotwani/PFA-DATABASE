"""Endpoint functional checks for D4 smoke testing."""

import base64
from dataclasses import dataclass, field
import requests

# Minimal valid 1x1 PNG bytes
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@dataclass
class SmokeRunner:
    """Tracks PASS/FAIL/SKIP results for smoke checks."""

    base_url: str
    session: requests.Session = field(default_factory=requests.Session)
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    def url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{path}"

    def record(self, name: str, ok: bool, detail: str = "") -> bool:
        tag = "PASS" if ok else "FAIL"
        suffix = f" ({detail})" if detail else ""
        print(f"[{tag}] {name}{suffix}")
        if ok:
            self.passed += 1
        else:
            self.failed += 1
        return ok

    def skip(self, name: str, reason: str) -> None:
        print(f"[SKIP] {name} ({reason})")
        self.skipped += 1


def auth_headers(token: str) -> dict[str, str]:
    """Return Bearer Authorization headers."""
    return {"Authorization": f"Bearer {token}"}


def login_user(runner: SmokeRunner, email: str, password: str, label: str) -> str:
    """Log in and return the JWT access token."""
    res = runner.session.post(
        runner.url("/api/auth/login"),
        json={"email": email, "password": password},
        timeout=15,
    )
    ok = res.status_code == 200 and "access_token" in res.json()
    runner.record(f"Login ({label})", ok, f"status={res.status_code}")
    return res.json().get("access_token", "") if ok else ""


def run_endpoint_checks(
    runner: SmokeRunner,
    admin_token: str,
    vol_token: str,
    safe_mode: bool,
) -> dict:
    """Execute endpoint smoke checks, skipping mutations when safe_mode=True."""
    ctx: dict = {"dog_id": None, "public_token": None}

    health = runner.session.get(runner.url("/api/health"), timeout=15)
    runner.record("GET /api/health", health.status_code == 200, f"status={health.status_code}")

    for role_lbl, tok in (("admin", admin_token), ("volunteer", vol_token)):
        me = runner.session.get(runner.url("/api/auth/me"), headers=auth_headers(tok), timeout=15)
        runner.record(f"GET /api/auth/me ({role_lbl})", me.status_code == 200)

    areas_res = runner.session.get(
        runner.url("/api/areas"), headers=auth_headers(vol_token), timeout=15
    )
    areas_ok = areas_res.status_code == 200 and len(areas_res.json().get("items", [])) > 0
    runner.record("GET /api/areas", areas_ok)
    area_id = areas_res.json()["items"][0]["id"] if areas_ok else None

    for path in ("/api/vaccinations/due", "/api/dashboard/stats"):
        res = runner.session.get(runner.url(path), headers=auth_headers(vol_token), timeout=15)
        runner.record(f"GET {path}", res.status_code == 200, f"status={res.status_code}")

    for path in (
        "/api/users",
        "/api/audit-logs",
        "/api/export/excel",
        "/api/analytics/export?format=json",
    ):
        res = runner.session.get(runner.url(path), headers=auth_headers(admin_token), timeout=30)
        runner.record(f"GET {path} (admin)", res.status_code == 200, f"status={res.status_code}")

    if safe_mode or area_id is None:
        runner.skip("Write lifecycle checks (dog/case/vax/photo/QR/change-password)", "--safe mode" if safe_mode else "no area")
        return ctx

    # Dog create/read/update as volunteer
    dog_res = runner.session.post(
        runner.url("/api/dogs"),
        headers=auth_headers(vol_token),
        json={
            "area_id": area_id,
            "sex": "female",
            "approx_age": "2 years",
            "age_group": "adult",
            "coat_description": "ZZ-SMOKE Brown",
            "guardian_phone": "+91-99999-00001",
            "landmark": "ZZ-SMOKE Gate",
        },
        timeout=15,
    )
    if runner.record("POST /api/dogs (volunteer)", dog_res.status_code == 201, f"status={dog_res.status_code}"):
        dog_json = dog_res.json()
        ctx["dog_id"] = dog_json["id"]
        ctx["public_token"] = dog_json["public_token"]
        ctx["vol_create_has_phone"] = "guardian_phone" in dog_json

        get_res = runner.session.get(runner.url(f"/api/dogs/{ctx['dog_id']}"), headers=auth_headers(vol_token), timeout=15)
        runner.record("GET /api/dogs/<id>", get_res.status_code == 200)

        upd_res = runner.session.patch(
            runner.url(f"/api/dogs/{ctx['dog_id']}"),
            headers=auth_headers(vol_token),
            json={"landmark": "ZZ-SMOKE Updated"},
            timeout=15,
        )
        runner.record("PATCH /api/dogs/<id>", upd_res.status_code == 200)

        case_res = runner.session.post(
            runner.url(f"/api/dogs/{ctx['dog_id']}/cases"),
            headers=auth_headers(vol_token),
            json={"pickup_date": "2026-11-28", "pre_op_notes": "ZZ-SMOKE case"},
            timeout=15,
        )
        runner.record("POST /api/dogs/<id>/cases", case_res.status_code == 201)

        vax_res = runner.session.post(
            runner.url(f"/api/dogs/{ctx['dog_id']}/vaccinations"),
            headers=auth_headers(vol_token),
            json={"vaccine_name": "Rabies", "date_given": "2026-11-28", "next_due_date": "2027-11-28"},
            timeout=15,
        )
        runner.record("POST /api/dogs/<id>/vaccinations", vax_res.status_code == 201)

        qr_res = runner.session.get(runner.url(f"/api/dogs/{ctx['dog_id']}/qr.png"), headers=auth_headers(vol_token), timeout=15)
        runner.record("GET /api/dogs/<id>/qr.png", qr_res.status_code == 200 and qr_res.headers.get("Content-Type", "").startswith("image/png"))

        photo_res = runner.session.post(
            runner.url(f"/api/dogs/{ctx['dog_id']}/photos"),
            headers=auth_headers(vol_token),
            files={"file": ("smoke.png", _TINY_PNG, "image/png")},
            timeout=30,
        )
        photo_ok = photo_res.status_code == 201 and bool(photo_res.json().get("url"))
        runner.record("POST /api/dogs/<id>/photos", photo_ok, f"status={photo_res.status_code}")
        if photo_ok:
            photo_url = photo_res.json()["url"]
            full_url = photo_url if photo_url.startswith("http") else runner.url(photo_url)
            fetch_res = requests.get(full_url, timeout=15)
            runner.record("GET uploaded photo URL", fetch_res.status_code == 200)

        pub_res = requests.get(runner.url(f"/api/public/dogs/{ctx['public_token']}"), timeout=15)
        runner.record("GET /api/public/dogs/<token>", pub_res.status_code == 200)

    # Verify change-password validation without altering real password
    cp_res = runner.session.post(
        runner.url("/api/auth/change-password"),
        headers=auth_headers(vol_token),
        json={"current_password": "ZZ-Wrong-Current-Password!", "new_password": "ZZ-New-Password-123!"},
        timeout=15,
    )
    runner.record("POST /api/auth/change-password (wrong current -> 401)", cp_res.status_code == 401)
    return ctx


def cleanup_smoke_data(runner: SmokeRunner, admin_token: str, ctx: dict) -> None:
    """Soft-delete temporary ZZ-SMOKE dog if created."""
    dog_id = ctx.get("dog_id")
    if not dog_id:
        return
    res = runner.session.delete(
        runner.url(f"/api/dogs/{dog_id}"),
        headers=auth_headers(admin_token),
        timeout=15,
    )
    runner.record("Cleanup soft-delete ZZ-SMOKE dog", res.status_code == 200)
