"""Application configuration loaded from environment variables."""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


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


class Config:
    """Base configuration for the Dog Sterilization API."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-fallback-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-jwt-fallback-key")
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

    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB upload limit

    # Cloudflare R2 configuration (used when STORAGE_BACKEND=r2)
    R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "")
    R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_PRESIGNED_URL_EXPIRY = int(os.getenv("R2_PRESIGNED_URL_EXPIRY", "3600"))

    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:5000").rstrip("/")
    NGO_CONTACT_TEXT = os.getenv(
        "NGO_CONTACT_TEXT", "Animal Welfare NGO Helpline"
    )