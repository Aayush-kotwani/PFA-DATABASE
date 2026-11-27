# Project Execution Status

- **Current Branch**: `security-hardening`
- **Current Step**: SEC-06..SEC-10 (Completed & verified; awaiting PASS before committing)
- **Steps Completed**:
  - Phase A (A1–A6) & Phase B (B1–B10) on `main`.
  - S0: Security Checklist and permanent security rules added to `PROJECT_CONTEXT.md`.
  - SEC-03: Strict production secret validation (`SECRET_KEY`, `JWT_SECRET_KEY` >= 32 chars, no placeholders).
  - SEC-05: `ProxyFix` middleware configured via `PROXY_FIX_COUNT`.
  - SEC-01: `Flask-Limiter` rate limiting on login (IP + email), public dog, photo upload, export, and QR endpoints with 429 JSON + `Retry-After`.
  - SEC-02: Formula/CSV injection sanitization (`sanitize_export_cell`) applied in Excel and streamed CSV exports (raw strings preserved in JSON).
  - SEC-04: `users.token_version` column migrated (`50a822f75e92`) and JWT revocation enforced on password reset, role change, and deactivation.
  - SEC-06: Security response headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `/api/*` `no-store`, `/media/*` `private, max-age=3600`, production HSTS).
  - SEC-07: Export audit logging (`action="export"`) for Excel and Analytics exports with row count and zero PII.
  - SEC-08: SQL `ILIKE` wildcard (`%`, `_`) escaping in dog search.
  - SEC-09: Image decompression-bomb protection (`MAX_IMAGE_PIXELS` -> 422) and per-dog active photo cap (`MAX_PHOTOS_PER_DOG` -> 409).
  - SEC-10: Request-ID structured logging, failed-login & admin-action logs, and safe generic 500 JSON handler.
- **Next Step**: SEC-11..SEC-15 (Swagger toggle, change-password, rotate-token, dependency pinning, debug/seed prod guards)
- **Known Issues**: None
