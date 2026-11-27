# Dog Sterilization Management System — Backend API

A modular Flask / APIFlask REST API for managing street dog rescue, sterilization surgeries, vaccinations, photos (Local & Cloudflare R2), QR code public verification, audit logs, and analytics exports.

## Prerequisites
- Python 3.11+
- PostgreSQL database (e.g. Neon Serverless PostgreSQL)
- Cloudflare R2 bucket & API token (for `STORAGE_BACKEND=r2`)

## 1. Local Setup
From the repository root (`pfa new db app/`):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Copy the environment template and fill in your values:
```powershell
Copy-Item backend\.env.example backend\.env
```

## 2. Environment Variables (`backend/.env`)
| Variable | Required | Description |
|---|---|---|
| `FLASK_ENV` | Yes | `development` or `production` |
| `SECRET_KEY` | Yes | Long random Flask session/app secret |
| `JWT_SECRET_KEY` | Yes | Long random JWT signing secret (>= 32 chars) |
| `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` | No | JWT lifetime in minutes (default `60`) |
| `DATABASE_URL` | Yes | PostgreSQL connection string (`?sslmode=require` for Neon) |
| `CORS_ORIGINS` | Yes | Comma-separated allowed frontend origins |
| `STORAGE_BACKEND` | Yes | `local` (dev) or `r2` (production / Cloudflare R2) |
| `UPLOAD_DIR` | When `local` | Local upload directory (default `uploads`) |
| `R2_ENDPOINT_URL` | When `r2` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `R2_BUCKET_NAME` | When `r2` | Private R2 bucket name |
| `R2_ACCESS_KEY_ID` | When `r2` | R2 API token Access Key ID (Object Read & Write) |
| `R2_SECRET_ACCESS_KEY` | When `r2` | R2 API token Secret Access Key |
| `R2_PRESIGNED_URL_EXPIRY` | No | Presigned GET URL lifetime in seconds (default `3600`) |
| `PUBLIC_BASE_URL` | Yes | Base URL encoded into dog QR codes (e.g. `http://localhost:5000`) |
| `NGO_CONTACT_TEXT` | Yes | Helpline text shown on public QR info responses |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | For seed | Initial admin account credentials for `scripts/seed.py` |
| `VOLUNTEER_EMAIL`, `VOLUNTEER_PASSWORD` | For seed | Initial volunteer account credentials for `scripts/seed.py` |

## 3. Database Migrations & Seeding
Run inside `backend/` with `.venv` active:
```powershell
cd backend
flask --app run db upgrade
python -m scripts.seed
```

## 4. Running the Server
Development server:
```powershell
cd backend
python run.py
```

Production WSGI server (Linux / Render):
```bash
gunicorn -w 2 -b 0.0.0.0:5000 run:app
```

## 5. Running Automated Tests
All `pytest` tests use an isolated in-memory SQLite database (`TestingConfig`) and never touch Neon or R2:
```powershell
cd backend
pytest
```

## 6. Swagger UI & Postman Import
- **Interactive Swagger UI**: Open `http://127.0.0.1:5000/docs` while the server is running.
  1. Call `POST /api/auth/login` to obtain an `access_token`.
  2. Click the green **Authorize** button at the top-right and paste the token.
- **Postman Import**: Import [`backend/openapi.json`](openapi.json) directly into Postman (**Import → File → `openapi.json`**) to get all endpoints, request schemas, and Bearer auth pre-configured.

## 7. Read-Only Analytics Role (BI / ML)
Run [`scripts/readonly_analytics_user.sql`](scripts/readonly_analytics_user.sql) in Neon SQL Editor (replacing the placeholder password) to create a `SELECT`-only `analytics_reader` PostgreSQL user for pandas, Metabase, or Power BI.
