"""Application configuration loaded from environment variables."""

from datetime import timedelta
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)

_PLACEHOLDER_PATTERNS = (
    "change-me",
    "replace-with",
    "dev-secret",
    "dev-jwt",
    "dev-only",
    "placeholder",
    "example",
)


def _parse_origins(raw_origins: str) -> list[str]:
    """Split comma-separated CORS origins into a clean list."""
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def _normalize_db_url(raw_url: str) -> str:
    """Ensure PostgreSQL URLs use the installed psycopg2 driver."""
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
        return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return raw_url


def validate_secret_strength(name: str, value: str) -> None:
    """Raise RuntimeError if a production secret is missing, short, or a placeholder."""
    cleaned = (value or "").strip()
    if not cleaned or len(cleaned) < 32:
        raise RuntimeError(
            f"{name} must be set and at least 32 characters long when FLASK_ENV=production."
        )
    lowered = cleaned.lower()
    if any(pattern in lowered for pattern in _PLACEHOLDER_PATTERNS):
        raise RuntimeError(
            f"{name} contains a known placeholder value and cannot be used in production."
        )


def _resolve_secret(name: str, dev_fallback: str) -> str:
    """Load secret from env; enforce strict rules in production, warn in dev."""
    val = os.getenv(name, "").strip()
    is_prod = os.getenv("FLASK_ENV", "development").strip().lower() == "production"
    if is_prod:
        validate_secret_strength(name, val)
        return val
    if not val:
        logger.warning("Using dev-only fallback for %s; configure a strong key in .env.", name)
        return dev_fallback
    return val


class Config:
    """Base configuration for the Dog Sterilization API."""

    FLASK_ENV = os.getenv("FLASK_ENV", "development").strip().lower()
    SECRET_KEY = _resolve_secret(
        "SECRET_KEY", "dev-only-insecure-secret-key-do-not-use-in-prod"
    )
    JWT_SECRET_KEY = _resolve_secret(
        "JWT_SECRET_KEY", "dev-only-insecure-jwt-key-do-not-use-in-prod"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60"))
    )

    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.getenv("DATABASE_URL", ""))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    CORS_ORIGINS = _parse_origins(
        os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )

    # Reverse proxy & Rate limiting
    PROXY_FIX_COUNT = int(os.getenv("PROXY_FIX_COUNT", "1"))
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").strip().lower() == "true"
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://").strip()
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200/minute").strip()
    RATELIMIT_LOGIN_IP = os.getenv("RATELIMIT_LOGIN_IP", "5/minute").strip()
    RATELIMIT_LOGIN_EMAIL = os.getenv("RATELIMIT_LOGIN_EMAIL", "5/minute").strip()
    RATELIMIT_PUBLIC_DOG = os.getenv("RATELIMIT_PUBLIC_DOG", "60/minute").strip()
    RATELIMIT_PHOTO_UPLOAD = os.getenv("RATELIMIT_PHOTO_UPLOAD", "10/minute").strip()
    RATELIMIT_EXPORT = os.getenv("RATELIMIT_EXPORT", "10/minute").strip()
    RATELIMIT_QR = os.getenv("RATELIMIT_QR", "30/minute").strip()

    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB upload limit
    MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "20000000"))
    MAX_PHOTOS_PER_DOG = int(os.getenv("MAX_PHOTOS_PER_DOG", "15"))

    # Cloudflare R2 configuration (used when STORAGE_BACKEND=r2)
    R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "")
    R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_PRESIGNED_URL_EXPIRY = int(os.getenv("R2_PRESIGNED_URL_EXPIRY", "3600"))

    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:5000").rstrip("/")
    NGO_CONTACT_TEXT = os.getenv("NGO_CONTACT_TEXT", "Animal Welfare NGO Helpline")


class TestingConfig(Config):
    """Isolated in-memory SQLite configuration for automated pytest runs."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    STORAGE_BACKEND = "local"
    RATELIMIT_ENABLED = False
    SECRET_KEY = "test-secret-key-at-least-32-bytes-long"
    JWT_SECRET_KEY = "test-jwt-secret-key-at-least-32-bytes-long"
    PUBLIC_BASE_URL = "http://localhost:5000"
    NGO_CONTACT_TEXT = "Test NGO Helpline: +91-00000-00000"
