# Project Context: Dog Sterilization Management System

## 1. Project Overview
A web-based management system for an animal welfare NGO in India that rescues, sterilizes, vaccinates, and releases street dogs (~30 dogs/month, 5-10 users).

- **Current Scope**: Backend API and PostgreSQL database only (No frontend during this phase).
- **Core Goal**: Digitize dog intake, surgery logs, vaccination tracking, photo documentation, GPS mapping, area identification, and public verification via QR code.

---

## 2. Technology Stack
- **Framework**: [APIFlask](https://apiflask.com/) (Flask wrapper with automatic OpenAPI / Swagger UI at `/docs` and Marshmallow schemas)
- **Database & ORM**: PostgreSQL with [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- **Migrations**: [Flask-Migrate](https://flask-migrate.readthedocs.io/) (Alembic)
- **Authentication**: [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/) (JWT bearer tokens)
- **CORS**: [Flask-CORS](https://flask-cors.readthedocs.io/)
- **Validation**: Marshmallow (integrated into APIFlask)
- **Image Processing**: Pillow (EXIF rotation fix, metadata stripping, resizing max 1200px, WebP conversion)
- **Storage Abstraction**: Pluggable storage interface (`LocalStorage` for dev, `R2Storage` / Cloudflare R2 via `boto3` for production)
- **Utilities**: `qrcode` (PNG generation), `openpyxl` (Excel export), `python-dotenv`, `gunicorn`, `psycopg2-binary`, `pytest`

---

## 3. Strict Architecture & Design Rules
1. **Modularity**:
   - One model per file (`backend/app/models/`).
   - One blueprint route per resource (`backend/app/routes/`).
   - Business logic isolated in `backend/app/services/`.
   - Validation & serialization in `backend/app/schemas/`.
   - Reusable utilities and decorators in `backend/app/utils/`.
   - File length limit: under ~200 lines per file.
2. **Security**:
   - Zero hardcoded secrets; configuration loaded from `.env` via `backend/app/config.py`.
   - Passwords hashed using secure algorithms (Werkzeug / bcrypt).
   - Public endpoint isolates and filters all private data.
3. **API Conventions**:
   - All API endpoints prefixed with `/api`.
   - Automatic Swagger documentation at `/docs`.
   - Standardized error format: `{"error": {"code": "...", "message": "..."}}`.
   - Standardized pagination response: `{"items": [...], "page": 1, "per_page": 20, "total": 100}`.
   - Soft deletes (`is_deleted = True`) excluded from standard queries.
   - Comprehensive audit logging on create, update, delete operations.
4. **Database Environment Separation Decision (Step A3 / Step A5)**:
   - Primary database provider: **Neon (Serverless PostgreSQL)**.
   - Development & test database: `pfa-dog-sterilization-db` is the standardized universal database used for development, testing, and migration verification.
   - Production database: A completely separate database instance/branch will be created and used exclusively for live production deployment later.
5. **Production Rules**:
   - Local disk storage (STORAGE_BACKEND=local) is for development ONLY. Production must use STORAGE_BACKEND=r2, because Render's disk is wiped on every restart or redeploy.
   - Production uses a separate Neon database, never `pfa-dog-sterilization-db` if that holds test data.
   - Production .env must have new strong SECRET_KEY, JWT_SECRET_KEY and admin/volunteer passwords, never the seed placeholders.
   - Debug mode must be off in production.

---

## 4. User Roles and Permissions
| Capability / Resource | Admin | Volunteer |
|---|---|---|
| View public dog information | Yes | Yes |
| View internal dog details | Yes | Yes |
| View `guardian_phone` | **Yes** | **NO (Stripped by serializer)** |
| Create dog (including setting guardian_phone) | Yes | Yes |
| Update dog details | Yes | Yes (guardian_phone is ignored if sent) |
| Create/Update cases & vaccinations | Yes | Yes |
| Upload dog photos | Yes | Yes |
| Soft-delete records (dogs, cases, photos, etc.) | **Yes** | **NO (Forbidden 403)** |
| Manage areas (create, edit, deactivate) | **Yes** | **NO (Forbidden 403)** |
| Manage users (create, edit roles, deactivate, reset passwords) | **Yes** | **NO (Forbidden 403)** |
| Export data to Excel | **Yes** | **NO (Forbidden 403)** |
| View audit logs | **Yes** | **NO (Forbidden 403)** |

---

## 5. Database Schema Summary
- **Common Mixins**:
  - `TimestampMixin`: `created_at` (timestamp, not null), `updated_at` (timestamp, auto-update)
  - `SoftDeleteMixin`: `is_deleted` (boolean, default false), `deleted_at` (timestamp, nullable)
- **Data Quality & Analytics Rules**:
  - Strict native SQL types: Date, DateTime, Numeric, Boolean, Enum (never store dates/numbers as plain text).
  - Soft-delete strategy across records to preserve historical and longitudinal analytical context.
  - Analytics-focused indexes on temporal queries: `dogs.created_at`, `cases.pickup_date`, `cases.surgery_date`, `cases.drop_date`.
- **Tables**:
  1. `users`: Authentication and role definitions (`admin`, `volunteer`).
  2. `areas`: Geographic operational zones with ward, unique color hex, and counter for dog code generation. (Uses `is_active`, no soft delete).
  3. `dogs`: Core animal profile, unique `dog_code`, unique `public_token`, GPS coordinates, sterilization status, guardian info, medical text. Analytics fields: `age_group` (Enum: puppy, young, adult, senior), `body_condition` (Enum: underweight, normal, overweight), `is_pregnant` (Boolean). [Soft Delete]
  4. `cases`: Individual pickup-to-release episodes, surgery details, prescription, surgeon name. Analytics fields: `surgery_outcome` (Enum: success, complication, death), `complication_type` (String 100), `recovery_days` (Integer). [Soft Delete]
  5. `vaccinations`: Vaccination records with vaccine name, date given, and next due date. [Soft Delete]
  6. `dog_photos`: Photos associated with dogs/cases, storage key, type (`intake`, `post_surgery`, `release`, `other`), primary flag. [Soft Delete]
  7. `audit_logs`: Immutable tracking table of data mutations (`create`, `update`, `delete`), table name, record ID, and JSONB diffs.

---

## 6. Directory Structure
```
pfa new db app/
├── .gitignore                      # Git ignore rules for Python, media, env
├── PROJECT_CONTEXT.md              # Project specifications, rules, progress tracker
├── STATUS.md                       # Current execution state and immediate next steps
└── backend/
    ├── app/                        # Main application package (Application Factory)
    │   ├── __init__.py             # Factory function (create_app)
    │   ├── config.py               # Config classes (Development, Production, Testing)
    │   ├── extensions.py           # Extensions (db, migrate, jwt, cors, api)
    │   ├── models/                 # Database models (one file per table + mixins)
    │   ├── routes/                 # API blueprints per resource
    │   ├── schemas/                # Request validation and serialization schemas
    │   ├── services/               # Pure business logic and domain services
    │   │   └── storage/            # Storage abstraction (LocalStorage, R2Storage)
    │   └── utils/                  # Helpers, custom decorators, error handlers
    ├── migrations/                 # Alembic database migration scripts
    ├── scripts/                    # Maintenance and seeding scripts (e.g., seed.py)
    └── tests/                      # Pytest automated test suite
```

---

## 7. Progress & Step Tracker

### Phase A - Foundation and Database
- [x] **A1**: Recommend and create project folder structure, `.gitignore`, Git repo initialization, `PROJECT_CONTEXT.md`, and `STATUS.md`.
- [x] **A2**: Virtual environment, dependencies (`requirements.txt`), minimal APIFlask app-factory, config from `.env`, CORS, and `/api/health` check.
- [x] **A3**: PostgreSQL setup (Neon `pfa-dog-sterilization-db`), database connectivity verification (`SELECT 1`).
- [x] **A4**: SQLAlchemy models (one file per table, mixins for timestamps and soft delete, analytics readiness columns, exports).
- [x] **A5**: Flask-Migrate setup, initial migration generation and execution, table verification.
- [x] **A6**: Safe database seeding script (`scripts/seed.py`) with admin, volunteer, and sample areas (Phase A Complete).

### Phase B - Backend APIs (Tested in Swagger UI)
- [x] **B1**: Authentication (`POST /api/auth/login`, `GET /api/auth/me`, password hashing, role decorators).
- [x] **B2**: User management (Admin only: list, create, update, password reset).
- [x] **B3**: Areas management (Staff list/read, Admin create/update/deactivate, color validation).
- [x] **B4**: Dogs CRUD (Safe dog code generation, role-filtered serialization, filtering/search, pagination).
- [x] **B5**: Cases CRUD (Nested under dog, lifecycle tracking from intake to release).
- [x] **B6**: Vaccinations CRUD & Due queries (`GET /api/vaccinations/due`).
- [x] **B7**: Photo upload & processing (Storage abstraction, LocalStorage, EXIF fix, WebP conversion).
- [x] **B7b**: Cloudflare R2 setup (account, private bucket, API token, R2Storage class, STORAGE_BACKEND=r2 switch, real upload test). MUST be done before deploying to Render.
- [x] **B8**: QR Code generation (`GET /api/dogs/{id}/qr.png`) & Public Verification (`GET /api/public/dogs/{public_token}`).
- [x] **B9**: Dashboard analytics, Audit log inspection, Admin Excel export, Analytics export endpoint (`GET /api/analytics/export` flat joined CSV/JSON with default PII exclusion) and read-only PostgreSQL role guidance for BI tools.
- [ ] **B10**: Hardening, automated tests (`pytest`), index checks, documentation (`README.md`), OpenAPI spec export.
