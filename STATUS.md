# Project Execution Status

- **Current Branch**: `security-hardening`
- **Current Step**: SEC-11..SEC-15 (Completed & verified; awaiting PASS before committing)
- **Steps Completed**:
  - Phase A (A1–A6) & Phase B (B1–B10) on `main`.
  - S0: Security Checklist and permanent security rules added to `PROJECT_CONTEXT.md`.
  - SEC-01..SEC-10: Committed (`af63274`) on `security-hardening`.
  - SEC-11: `ENABLE_SWAGGER` toggle disabling `/docs` and `/openapi.json` in production by default.
  - SEC-15: Removed hardcoded `debug=True` in `run.py` and guarded `scripts/seed.py` against production or placeholder passwords.
  - SEC-12: Self-service `POST /api/auth/change-password` with rate limit, `token_version` revocation, and audit logging.
  - SEC-13: Admin-only `POST /api/dogs/<id>/rotate-token` with rate limit and immediate old-token invalidation.
  - SEC-14: Exact version pinning in `backend/requirements.txt` and `pip-audit` vulnerability verification.
- **Next Step**: Merge `security-hardening` into `main` after final review, then proceed to Frontend (Phase C).
- **Known Issues**: None
