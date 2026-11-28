# Dog Sterilization Management System — Backend API

A modular, security-hardened **APIFlask** REST API for managing street dog rescue, sterilization surgeries, vaccinations, photos (Local & Cloudflare R2), QR-based public verification, audit trails, and analytics exports.

---

## 1. Tech Stack
- **Web & OpenAPI**: Python 3.11+, APIFlask (`marshmallow` validation + Swagger `/docs` & `/openapi.json`)
- **Database & Migrations**: PostgreSQL (Neon Serverless), Flask-SQLAlchemy, Alembic (`Flask-Migrate`)
- **Authentication & Security**: `Flask-JWT-Extended` (stateless JWT + DB `token_version` revocation), `Flask-Limiter` (rate limiting), `ProxyFix`, security headers, formula-injection sanitization
- **Media & Exports**: `Pillow` (EXIF orientation fix + metadata strip + max 1200px WebP), `boto3` (Cloudflare R2 private bucket + presigned URLs), `qrcode`, `openpyxl`
- **Server & Testing**: `gunicorn` (WSGI), `pytest` (isolated in-memory SQLite `TestingConfig`)

---

## 2. Layered Architecture & Folder Map

Every request follows a strict one-way layered flow:

```text
HTTP Request
   │
   ▼
Routes (Blueprints: app/routes/*.py)       ── Rate limits, JWT/role guards, OpenAPI docs
   │
   ▼
Schemas (Marshmallow: app/schemas/*.py)    ── Input validation, role-aware output filtering
   │
   ▼
Services (app/services/*.py)               ── Business logic, transactions, audit logging
   │
   ▼
Models (SQLAlchemy: app/models/*.py)       ── Tables, constraints, Timestamp & SoftDelete mixins
   │
   ▼
PostgreSQL (Neon) / Object Storage (Local or R2)
```

### Key Directories
- `backend/app/__init__.py` — App factory (`create_app`), `ProxyFix`, JWT loaders, `ENABLE_SWAGGER` toggle, error handlers, security headers, blueprint registration.
- `backend/app/config.py` — `Config` and `TestingConfig`, production secret enforcement (`SECRET_KEY`, `JWT_SECRET_KEY` ≥ 32 chars, no placeholders).
- `backend/app/utils/` — Cross-cutting helpers:
  - `auth.py` — `@login_required`, `@roles_required(...)`, `token_version` verification.
  - `errors.py` — `APIError`, consistent `{"error": {"code", "message"}}` JSON, safe generic `500` handler.
  - `pagination.py` — Shared `paginate_query()` helper.
  - `rate_limit.py` — Per-user/IP and per-email rate limit key functions.
  - `security_headers.py` — `nosniff`, `DENY`, `no-referrer`, `Permissions-Policy`, `/api/*` `no-store`, `/media/*` cache policy, production HSTS.
  - `export_sanitize.py` — Escapes `=`, `+`, `-`, `@`, tab, CR in Excel/CSV cells.
  - `search.py` — Escapes `%` and `_` in SQL `ILIKE` queries.
  - `images.py` — Decompression-bomb guard (`MAX_IMAGE_PIXELS`), EXIF fix/strip, WebP conversion.
  - `logging.py` — `X-Request-ID` correlation filter and structured security logging.
- `backend/app/services/storage/` — Storage abstraction (`StorageBackend` → `LocalStorage` / `R2Storage`).
- `backend/scripts/` — `seed.py` (guarded dev/initial seeding) and `readonly_analytics_user.sql` (BI/ML read-only Postgres role).

---

## 3. End-to-End Application Flows

### A. Auth & RBAC Flow
1. User calls `POST /api/auth/login` (rate-limited by IP + email).
2. `auth_service.authenticate_user()` verifies password hash and `is_active`, then issues a JWT containing `token_version`.
3. Every protected route runs `@login_required` (and `@roles_required("admin")` for admin-only routes), checking both `user.is_active` and `jwt_payload["token_version"] == user.token_version`.
4. Volunteers have sensitive PII (`guardian_phone`) stripped in `Dog` serialization; only admins receive it.
5. Changing password (`POST /api/auth/change-password`), admin password reset, role change, or user deactivation increments `user.token_version`, immediately revoking all older JWTs.

### B. Dog Lifecycle Flow (Areas → Dogs → Cases → Vaccinations)
1. **Areas**: Admin defines operational zones with unique `short_code` (e.g. `CTR`) and hex color.
2. **Dogs**: Staff registers a dog (`POST /api/dogs`). `dog_service` row-locks the `Area` (`WITH FOR UPDATE`) to atomically increment `last_dog_number`, generating `dog_code` (e.g. `CTR-0001`) and a random `public_token`.
3. **Cases**: Staff opens a sterilization case (`POST /api/dogs/<id>/cases`) and updates pickup → surgery → drop dates/status. Case transitions automatically sync `dog.status` and compute `recovery_days`.
4. **Vaccinations**: Staff records vaccinations (`POST /api/dogs/<id>/vaccinations`) with `next_due_date`. `GET /api/vaccinations/due` classifies upcoming and overdue boosters.

### C. Photo Pipeline Flow
1. Staff uploads multipart image (`POST /api/dogs/<id>/photos`, rate-limited and capped by `MAX_PHOTOS_PER_DOG`).
2. `utils/images.py` checks file size (≤ 10 MB), allowed formats (`JPEG`/`PNG`/`WEBP`), and pixel count (`MAX_IMAGE_PIXELS` → `422` on decompression bombs).
3. `Pillow` applies EXIF orientation (`exif_transpose`), strips all EXIF/GPS metadata, resizes to max `1200px`, and encodes to WebP.
4. `get_storage()` saves the WebP under a random UUID key to `LocalStorage` (served via `/media/<key>`) or private `R2Storage` (served via time-limited presigned URLs).

### D. Public QR Flow
1. Staff downloads `GET /api/dogs/<id>/qr.png`, encoding `PUBLIC_BASE_URL/d/<public_token>`.
2. Anyone scanning the QR hits `GET /api/public/dogs/<public_token>` (unauthenticated, rate-limited).
3. `public_service` returns **strictly non-PII allow-listed fields** (dog code, area name/color, primary photo URL, sterilization status, vaccinations, NGO helpline) and returns `404` for soft-deleted dogs.
4. Admin can invalidate a compromised QR anytime via `POST /api/dogs/<id>/rotate-token`.

### E. Reporting, Audit & Analytics Flow
1. `GET /api/dashboard/stats` aggregates non-deleted counts by status, area, and monthly sterilization trends.
2. Mutations and exports (`action="export"`) write structured records to `audit_logs` (admin-only inspection via `GET /api/audit-logs`).
3. Admin exports:
   - `GET /api/export/excel` — 3-sheet `.xlsx` (`Dogs`, `Cases`, `Vaccinations`) with formula-sanitized cells.
   - `GET /api/analytics/export` — Flat joined dataset in streamed `csv` (formula-sanitized) or `json` (raw values); personal data (`guardian_name`, `guardian_phone`, `capture_address`) is **excluded by default** (`include_personal=false`).
4. BI/ML tools (pandas, Metabase, Power BI) can connect directly using the `SELECT`-only `analytics_reader` role defined in [`scripts/readonly_analytics_user.sql`](scripts/readonly_analytics_user.sql).

---

## 4. Local Setup & Environment Variables

From the repository root (`pfa new db app/`):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Key environment variables in `backend/.env` (see [`backend/.env.example`](.env.example) for defaults):
- **Core & Secrets**: `FLASK_ENV` (`development`/`production`), `FLASK_DEBUG` (`0`), `SECRET_KEY`, `JWT_SECRET_KEY` (≥ 32 chars in production), `JWT_ACCESS_TOKEN_EXPIRES_MINUTES`, `ENABLE_SWAGGER` (`true` in dev; disabled in prod unless `true`).
- **Database & CORS**: `DATABASE_URL` (`?sslmode=require` for Neon), `CORS_ORIGINS`, `PROXY_FIX_COUNT`.
- **Storage**: `STORAGE_BACKEND` (`local` or `r2`), `UPLOAD_DIR`, `R2_ENDPOINT_URL`, `R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_PRESIGNED_URL_EXPIRY`.
- **Public QR & Limits**: `PUBLIC_BASE_URL`, `NGO_CONTACT_TEXT`, `MAX_IMAGE_PIXELS`, `MAX_PHOTOS_PER_DOG`, and `RATELIMIT_*` variables.
- **Seeding (dev/initial only)**: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `VOLUNTEER_EMAIL`, `VOLUNTEER_PASSWORD`.

---

## 5. Migrations, Seeding, Running & Testing

Run inside `backend/` with `.venv` active:
```powershell
cd backend

# Apply migrations
flask --app run db upgrade

# Seed initial users & areas (blocked in production or with placeholder passwords)
python -m scripts.seed

# Run development server
python run.py

# Run production WSGI server (Linux / Render)
gunicorn -w 2 -b 0.0.0.0:5000 run:app

# Run automated test suite (isolated in-memory SQLite DB; never touches Neon)
pytest -v
```

---

## 6. Swagger UI & Postman Import
- **Swagger UI**: Open `http://127.0.0.1:5000/docs` in development (`ENABLE_SWAGGER=true`), log in via `POST /api/auth/login`, and click **Authorize** to paste your Bearer token.
- **Postman**: Import [`backend/openapi.json`](openapi.json) directly into Postman for all 27 endpoint paths, schemas, and Bearer auth.

---

## 7. Render Production Deployment Checklist
1. Set `FLASK_ENV=production`, `FLASK_DEBUG=0`, `ENABLE_SWAGGER=false`, and `PROXY_FIX_COUNT=1`.
2. Generate unique 64-char random values for `SECRET_KEY` and `JWT_SECRET_KEY`.
3. Configure production Neon `DATABASE_URL`, production `CORS_ORIGINS`, `PUBLIC_BASE_URL`, and `STORAGE_BACKEND=r2` with production R2 credentials.
4. Run `flask --app run db upgrade` against the production database before starting `gunicorn -w 2 -b 0.0.0.0:$PORT run:app`.
5. Keep all `RATELIMIT_*`, `MAX_IMAGE_PIXELS`, and `MAX_PHOTOS_PER_DOG` limits active.
