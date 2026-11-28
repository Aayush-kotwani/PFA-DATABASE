# Production Deployment Guide (Render + Neon + Cloudflare R2)

This guide covers deploying the Dog Sterilization Management Backend to **Render** (`Singapore`), backed by **Neon PostgreSQL** and **Cloudflare R2**.

---

## 1. Prerequisites
- A dedicated **production** Neon database (separate from `pfa-dog-sterilization-db`) with `?sslmode=require`.
- A dedicated **private** Cloudflare R2 bucket and API token (Object Read & Write).
- Two fresh random 64-character secrets generated locally (never use words like `change-me`, `example`, or `placeholder`):
  ```powershell
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

---

## 2. Render Setup

### Option A: Render Blueprint (`render.yaml`) — Recommended
1. Push your branch/PR to GitHub and merge into `main`.
2. In Render Dashboard, click **New → Blueprint**, connect the repo, and select `render.yaml`.
3. Render automatically creates `pfa-dog-sterilization-api` (`rootDir: backend`, `region: singapore`, `PYTHON_VERSION=3.11.9`) with all non-secret defaults pre-filled.
4. Fill in every `sync: false` environment variable in Render's prompt/Dashboard (see Section 3).

### Option B: Manual Web Service
1. **New → Web Service** → connect your GitHub repository.
2. Set **Root Directory**: `backend`, **Region**: `Singapore`, **Runtime**: `Python 3`.
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `gunicorn -c gunicorn.conf.py run:app`
5. **Health Check Path**: `/api/health` and **Auto-Deploy**: `Yes`.
6. Add `PYTHON_VERSION=3.11.9` and all environment variables from Section 3.

---

## 3. Environment Variables

| Variable | Secret (`sync: false`) | Production Value / Notes |
|---|---|---|
| `SECRET_KEY` | **Yes** | Pure random string from `secrets.token_urlsafe(48)` |
| `JWT_SECRET_KEY` | **Yes** | Different pure random string from `secrets.token_urlsafe(48)` |
| `DATABASE_URL` | **Yes** | Production Neon pooler URL (`postgresql://...?sslmode=require`) |
| `R2_ACCESS_KEY_ID` | **Yes** | Production R2 Access Key ID |
| `R2_SECRET_ACCESS_KEY` | **Yes** | Production R2 Secret Access Key |
| `R2_ENDPOINT_URL` | Dashboard (`sync: false`) | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `R2_BUCKET_NAME` | Dashboard (`sync: false`) | Production private R2 bucket name |
| `CORS_ORIGINS` | Dashboard (`sync: false`) | Frontend origin (e.g. `https://app.your-ngo.org`) |
| `PUBLIC_BASE_URL` | Dashboard (`sync: false`) | `https://<your-api-or-frontend-domain>` |
| `NGO_CONTACT_TEXT` | Dashboard (`sync: false`) | Official NGO helpline text for QR pages |
| `FLASK_ENV` | No | `production` |
| `FLASK_DEBUG` | No | `0` |
| `ENABLE_SWAGGER` | No | `false` (disables `/docs` and `/openapi.json`) |
| `PROXY_FIX_COUNT` | No | `1` |
| `STORAGE_BACKEND` | No | `r2` |
| `RATELIMIT_*` / `MAX_*` | No | Defaults set in `render.yaml` |

Validate your values locally before deploying using `backend/scripts/check_prod_env.py` in a temporary PowerShell session.

---

## 4. Database Migrations (Free vs Paid Plans)
- **Free plan** (`plan: free`): Render disables `preDeployCommand` on Free services. Run migrations once from your computer in a temporary shell session before/after deploy:
  ```powershell
  cd backend
  $env:FLASK_ENV="production"
  $env:SECRET_KEY="<prod-secret>"
  $env:JWT_SECRET_KEY="<prod-jwt-secret>"
  $env:DATABASE_URL="<prod-neon-url>"
  ..\.venv\Scripts\flask --app run db upgrade
  ```
- **Paid plan** (`starter` or higher): Uncomment `preDeployCommand: flask --app run db upgrade` in `render.yaml` so migrations run automatically on every deploy.

---

## 5. First-Admin Creation & Smoke Verification
1. `scripts/seed.py` is blocked in production. Create the first admin interactively (password is prompted hidden via `getpass`):
   ```powershell
   cd backend
   $env:FLASK_ENV="production"; $env:SECRET_KEY="<prod>"; $env:JWT_SECRET_KEY="<prod>"
   $env:DATABASE_URL="<prod-neon-url>"; $env:ADMIN_EMAIL="admin@your-ngo.org"
   ..\.venv\Scripts\python.exe -m scripts.create_admin
   ```
2. Verify the live deployment in read-only mode:
   ```powershell
   $env:BASE_URL="https://<your-service>.onrender.com"
   $env:SMOKE_ADMIN_EMAIL="admin@your-ngo.org"; $env:SMOKE_ADMIN_PASSWORD="<admin-pw>"
   $env:SMOKE_VOLUNTEER_EMAIL="<vol-email>"; $env:SMOKE_VOLUNTEER_PASSWORD="<vol-pw>"
   ..\.venv\Scripts\python.exe backend\scripts\smoke_test.py --safe
   ```

---

## 6. Operations: Logs, Rollback, Secret Rotation, Neon Restore & Frontend Go-Live
- **Checking Logs**: Render Dashboard → Service → **Logs**. Search by request correlation ID (`[req=...]`, returned in every `X-Request-ID` response header).
- **Rollback a Bad Deploy**: Render Dashboard → **Deploys** → select the last healthy deploy → **Rollback to this deploy**. (If a migration was applied, check `flask db downgrade` before rolling back code.)
- **Rotating Secrets**:
  - `SECRET_KEY` / `JWT_SECRET_KEY`: Generate new `secrets.token_urlsafe(48)` values in Render → Save & Deploy (invalidates all active JWTs immediately).
  - `DATABASE_URL` / R2 keys: Rotate the password/token in Neon or Cloudflare R2, update the env var in Render, and redeploy.
  - Compromised QR link: Call `POST /api/dogs/<id>/rotate-token` as Admin.
- **Restoring Database from Neon Backups**: In Neon Console → **Branches / Restore** (Point-in-Time Recovery), create a branch from before the incident, verify data, then either promote/restore the primary branch or point `DATABASE_URL` to the restored branch.
- **When the Frontend Goes Live**: In Render Dashboard → **Environment**, update `CORS_ORIGINS` to your live frontend `https://` origin and `PUBLIC_BASE_URL` to your live frontend QR base URL (`https://app.your-ngo.org`), then redeploy.
