"""Verify production environment variables without printing any secret or env values."""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import validate_secret_strength  # noqa: E402


def _check_secret(name: str) -> bool:
    """Validate a secret key is >= 32 chars and free of placeholder markers."""
    val = os.getenv(name, "")
    try:
        validate_secret_strength(name, val)
        return True
    except RuntimeError:
        return False


def _check_database_url() -> bool:
    """Ensure DATABASE_URL uses PostgreSQL with sslmode=require and is not dev DB."""
    db_url = os.getenv("DATABASE_URL", "").strip()
    lowered = db_url.lower()
    if not (lowered.startswith("postgresql://") or lowered.startswith("postgres://")):
        return False
    if "sslmode=require" not in lowered:
        return False
    if "pfa-dog-sterilization-db" in lowered:
        return False
    return True


def _check_cors_origins() -> bool:
    """Ensure CORS_ORIGINS is set and does not contain wildcard '*'."""
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return False
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return bool(origins) and all(origin != "*" for origin in origins)


def _check_r2_storage() -> bool:
    """Ensure STORAGE_BACKEND=r2 and all required R2 variables are non-empty."""
    if os.getenv("STORAGE_BACKEND", "").strip().lower() != "r2":
        return False
    required = (
        "R2_ENDPOINT_URL",
        "R2_BUCKET_NAME",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
    )
    return all(bool(os.getenv(k, "").strip()) for k in required)


def run_checks() -> int:
    """Run all production readiness checks, printing only PASS/FAIL per check."""
    debug_raw = os.getenv("FLASK_DEBUG", "").strip().lower()
    checks: list[tuple[str, bool]] = [
        ("FLASK_ENV is production", os.getenv("FLASK_ENV", "").strip().lower() == "production"),
        ("FLASK_DEBUG is disabled", debug_raw in ("", "0", "false")),
        ("SECRET_KEY strength", _check_secret("SECRET_KEY")),
        ("JWT_SECRET_KEY strength", _check_secret("JWT_SECRET_KEY")),
        ("DATABASE_URL is non-dev Postgres with sslmode=require", _check_database_url()),
        ("CORS_ORIGINS is set and not wildcard", _check_cors_origins()),
        ("PUBLIC_BASE_URL uses https://", os.getenv("PUBLIC_BASE_URL", "").strip().lower().startswith("https://")),
        ("STORAGE_BACKEND=r2 with all R2 credentials", _check_r2_storage()),
        ("ENABLE_SWAGGER is disabled", os.getenv("ENABLE_SWAGGER", "").strip().lower() != "true"),
    ]

    failures = 0
    for label, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {label}")
        if not passed:
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run_checks())
