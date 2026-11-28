"""Security verification checks for D4 smoke testing."""

import uuid
import requests

from scripts.smoke_checks_endpoints import SmokeRunner, auth_headers, login_user

_PUBLIC_ALLOWED_KEYS = {
    "dog_code",
    "area_name",
    "area_color_name",
    "area_color_hex",
    "primary_photo_url",
    "sterilized",
    "latest_vaccination",
    "ngo_contact",
}


def run_security_checks(
    runner: SmokeRunner,
    admin_token: str,
    vol_token: str,
    ctx: dict,
    safe_mode: bool,
) -> None:
    """Run read-only and (optionally) write security checks."""
    if runner.base_url.startswith("https://"):
        http_url = "http://" + runner.base_url[len("https://"):]
        redir = requests.get(f"{http_url.rstrip('/')}/api/health", allow_redirects=False, timeout=15)
        runner.record("HTTP -> HTTPS redirect", redir.status_code in (301, 302, 307, 308))
    else:
        runner.skip("HTTP -> HTTPS redirect & HSTS", "local HTTP")

    health = requests.get(runner.url("/api/health"), timeout=15)
    h = health.headers
    headers_ok = (
        h.get("X-Content-Type-Options") == "nosniff"
        and h.get("X-Frame-Options") == "DENY"
        and h.get("Referrer-Policy") == "no-referrer"
        and h.get("Cache-Control") == "no-store"
    )
    runner.record("Security response headers", headers_ok)
    if runner.base_url.startswith("https://"):
        runner.record("Strict-Transport-Security header", "Strict-Transport-Security" in h)

    # Swagger disabled in production
    docs_res = requests.get(runner.url("/docs"), timeout=15)
    spec_res = requests.get(runner.url("/openapi.json"), timeout=15)
    if runner.base_url.startswith(("http://127.0.0.1", "http://localhost")) and spec_res.status_code == 200:
        runner.skip("Swagger/OpenAPI disabled", "intentionally enabled in local dev")
    else:
        runner.record("Swagger/OpenAPI disabled (404)", docs_res.status_code == 404 and spec_res.status_code == 404)

    # Unauthenticated 401 checks
    protected = [
        "/api/auth/me",
        "/api/users",
        "/api/areas",
        "/api/dogs",
        "/api/vaccinations/due",
        "/api/dashboard/stats",
        "/api/audit-logs",
        "/api/export/excel",
        "/api/analytics/export",
    ]
    unauth_ok = all(
        requests.get(runner.url(p), timeout=15).status_code == 401
        and "error" in requests.get(runner.url(p), timeout=15).json()
        for p in protected
    )
    runner.record("Unauthenticated protected routes return 401 JSON", unauth_ok)

    # Volunteer 403 checks
    vol_h = auth_headers(vol_token)
    rb_checks = [
        requests.get(runner.url("/api/users"), headers=vol_h, timeout=15).status_code == 403,
        requests.post(runner.url("/api/areas"), headers=vol_h, json={"name": "X", "short_code": "XXX", "ward_no": "Ward X", "color_name": "Red", "color_hex": "#FF0000"}, timeout=15).status_code == 403,
        requests.delete(runner.url("/api/dogs/1"), headers=vol_h, timeout=15).status_code == 403,
        requests.get(runner.url("/api/export/excel"), headers=vol_h, timeout=15).status_code == 403,
        requests.get(runner.url("/api/audit-logs"), headers=vol_h, timeout=15).status_code == 403,
        requests.get(runner.url("/api/analytics/export"), headers=vol_h, timeout=15).status_code == 403,
    ]
    runner.record("Volunteer blocked (403) on admin routes", all(rb_checks))

    # Phone isolation check
    adm_h = auth_headers(admin_token)
    if ctx.get("dog_id"):
        v_dog = requests.get(runner.url(f"/api/dogs/{ctx['dog_id']}"), headers=vol_h, timeout=15).json()
        a_dog = requests.get(runner.url(f"/api/dogs/{ctx['dog_id']}"), headers=adm_h, timeout=15).json()
        v_list = requests.get(runner.url("/api/dogs?search=ZZ-SMOKE"), headers=vol_h, timeout=15).json().get("items", [])
        phone_ok = (
            not ctx.get("vol_create_has_phone", False)
            and "guardian_phone" not in v_dog
            and all("guardian_phone" not in item for item in v_list)
            and "guardian_phone" in a_dog
        )
        runner.record("Volunteer guardian_phone isolation", phone_ok)
    else:
        v_list = requests.get(runner.url("/api/dogs"), headers=vol_h, timeout=15).json().get("items", [])
        runner.record("Volunteer guardian_phone stripped in list", all("guardian_phone" not in i for i in v_list))

    # Public endpoint allowlist & 404 parity
    bad_pub = requests.get(runner.url("/api/public/dogs/nonexistent-token-zz"), timeout=15)
    if ctx.get("public_token"):
        pub_json = requests.get(runner.url(f"/api/public/dogs/{ctx['public_token']}"), timeout=15).json()
        runner.record("Public endpoint strict 8-field allowlist", set(pub_json.keys()) == _PUBLIC_ALLOWED_KEYS)
        rot_res = requests.post(runner.url(f"/api/dogs/{ctx['dog_id']}/rotate-token"), headers=adm_h, timeout=15)
        old_after = requests.get(runner.url(f"/api/public/dogs/{ctx['public_token']}"), timeout=15)
        runner.record(
            "Public token rotation invalidates old token (404 parity)",
            rot_res.status_code == 200 and old_after.status_code == 404 and bad_pub.status_code == 404,
        )
    else:
        runner.record("Public unknown token returns 404", bad_pub.status_code == 404)

    # Error responses never leak stack traces & CORS omits evil origin
    err_res = requests.get(runner.url("/api/dogs/99999999"), headers=vol_h, timeout=15)
    runner.record("Errors omit stack traces", "Traceback" not in err_res.text)

    cors_res = requests.get(runner.url("/api/health"), headers={"Origin": "https://evil-example.com"}, timeout=15)
    runner.record("CORS omits Access-Control-Allow-Origin for untrusted origin", "Access-Control-Allow-Origin" not in cors_res.headers)

    if safe_mode:
        runner.skip("Write security checks (mass assignment, fake upload, token revocation, rate limit)", "--safe mode")
        return

    # Mass assignment rejected
    mass_res = requests.post(
        runner.url("/api/dogs"),
        headers=vol_h,
        json={"area_id": 1, "sex": "male", "approx_age": "1y", "age_group": "adult", "coat_description": "Black", "is_deleted": True, "public_token": "evil"},
        timeout=15,
    )
    runner.record("Mass assignment rejected (422)", mass_res.status_code == 422)

    # Fake image upload rejected
    if ctx.get("dog_id"):
        fake_res = requests.post(
            runner.url(f"/api/dogs/{ctx['dog_id']}/photos"),
            headers=vol_h,
            files={"file": ("fake.jpg", b"<html><body>not a jpg</body></html>", "image/jpeg")},
            timeout=15,
        )
        runner.record("Fake image upload rejected (400)", fake_res.status_code == 400)

    # Throwaway user deactivation revokes JWT
    tmp_email = f"zz-smoke-{uuid.uuid4().hex[:8]}@ngo.org"
    tmp_pw = "SmokeTempPass123!"
    cu = requests.post(
        runner.url("/api/users"),
        headers=adm_h,
        json={"name": "ZZ Smoke Temp", "email": tmp_email, "password": tmp_pw, "role": "volunteer"},
        timeout=15,
    )
    if cu.status_code == 201:
        tmp_id = cu.json()["id"]
        tmp_tok = login_user(runner, tmp_email, tmp_pw, "temp user")
        requests.patch(runner.url(f"/api/users/{tmp_id}"), headers=adm_h, json={"is_active": False}, timeout=15)
        revoked = requests.get(runner.url("/api/auth/me"), headers=auth_headers(tmp_tok), timeout=15)
        runner.record("Deactivated user access blocked (401/403)", revoked.status_code in (401, 403))

    # Login rate limit check LAST
    got_429 = False
    has_retry_after = False
    for _ in range(10):
        r = requests.post(
            runner.url("/api/auth/login"),
            json={"email": f"zz-ratelimit-{uuid.uuid4().hex[:6]}@ngo.org", "password": "WrongPassword123!"},
            timeout=15,
        )
        if r.status_code == 429:
            got_429 = True
            has_retry_after = "Retry-After" in r.headers
            break
    runner.record("Login rate limit returns 429 with Retry-After", got_429 and has_retry_after)
