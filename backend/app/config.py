"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _parse_origins(raw_origins: str) -> list[str]:
    """Split comma-separated CORS origins into a clean list."""
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


class Config:
    """Base configuration for the Dog Sterilization API."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-fallback-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-jwt-fallback-key")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = _parse_origins(
        os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )

    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB upload limit

    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:5000").rstrip("/")
    NGO_CONTACT_TEXT = os.getenv(
        "NGO_CONTACT_TEXT", "Animal Welfare NGO Helpline"
    )