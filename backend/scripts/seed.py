"""Idempotent database seeding script for development and initial deployment."""

import os
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

# Ensure backend root is on sys.path when script is executed directly
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models import Area, User


_PLACEHOLDER_PASSWORDS = {
    "change-me-admin-password",
    "change-me-volunteer-password",
}


def _validate_credentials() -> tuple[str, str, str, str]:
    """Retrieve and validate seed credentials from environment variables."""
    env_name = os.getenv("FLASK_ENV", "development").strip().lower()
    if env_name == "production":
        raise RuntimeError("Refusing to run seed.py in production environment.")

    admin_email = os.getenv("ADMIN_EMAIL", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    volunteer_email = os.getenv("VOLUNTEER_EMAIL", "").strip()
    volunteer_password = os.getenv("VOLUNTEER_PASSWORD", "").strip()

    missing = []
    if not admin_email:
        missing.append("ADMIN_EMAIL")
    if not admin_password:
        missing.append("ADMIN_PASSWORD")
    if not volunteer_email:
        missing.append("VOLUNTEER_EMAIL")
    if not volunteer_password:
        missing.append("VOLUNTEER_PASSWORD")

    if missing:
        raise ValueError(
            f"Missing required environment variables for seeding: {', '.join(missing)}. "
            "Please configure them in your .env file."
        )

    for label, pw in [
        ("ADMIN_PASSWORD", admin_password),
        ("VOLUNTEER_PASSWORD", volunteer_password),
    ]:
        if "change-me" in pw.lower() or pw in _PLACEHOLDER_PASSWORDS:
            raise RuntimeError(
                f"Refusing to run seed.py with placeholder password in {label}."
            )

    return admin_email, admin_password, volunteer_email, volunteer_password


def seed_database() -> dict[str, int]:
    """Seed initial admin, volunteer, and 3 sample geographic operational areas."""
    admin_email, admin_password, volunteer_email, volunteer_password = _validate_credentials()

    app = create_app()
    stats = {"users_created": 0, "users_skipped": 0, "areas_created": 0, "areas_skipped": 0}

    with app.app_context():
        # 1. Seed Users (Admin and Volunteer)
        seed_users = [
            {
                "name": "NGO Admin",
                "email": admin_email,
                "password": admin_password,
                "role": "admin",
            },
            {
                "name": "NGO Volunteer",
                "email": volunteer_email,
                "password": volunteer_password,
                "role": "volunteer",
            },
        ]

        print("--- Seeding Users ---")
        for u in seed_users:
            existing = User.query.filter_by(email=u["email"]).first()
            if existing:
                print(f"  [SKIP] User '{u['email']}' already exists (id={existing.id}, role='{existing.role}').")
                stats["users_skipped"] += 1
            else:
                user = User(
                    name=u["name"],
                    email=u["email"],
                    password_hash=generate_password_hash(u["password"]),
                    role=u["role"],
                    is_active=True,
                )
                db.session.add(user)
                print(f"  [CREATE] Added user '{u['email']}' with role '{u['role']}'.")
                stats["users_created"] += 1

        # 2. Seed 3 Sample Areas with distinct names, colors, and ward numbers
        seed_areas = [
            {
                "name": "Central Zone - Ward 1",
                "short_code": "CTR",
                "ward_no": "Ward 1",
                "color_name": "Teal",
                "color_hex": "#0D9488",
                "landmark": "Near Municipal Clock Tower",
                "animal_lover_name": "Sunita Sharma",
                "animal_lover_phone": "+91-98765-43210",
            },
            {
                "name": "North Market - Ward 2",
                "short_code": "NMT",
                "ward_no": "Ward 2",
                "color_name": "Amber",
                "color_hex": "#D97706",
                "landmark": "Opposite Vegetable Wholesale Yard",
                "animal_lover_name": "Rajesh Patel",
                "animal_lover_phone": "+91-98765-43211",
            },
            {
                "name": "Station Road - Ward 3",
                "short_code": "STR",
                "ward_no": "Ward 3",
                "color_name": "Indigo",
                "color_hex": "#4F46E5",
                "landmark": "Platform 1 Auto Stand Gate",
                "animal_lover_name": "Pooja Verma",
                "animal_lover_phone": "+91-98765-43212",
            },
        ]

        print("\n--- Seeding Operational Areas ---")
        for a in seed_areas:
            existing = Area.query.filter(
                (Area.short_code == a["short_code"]) | (Area.name == a["name"])
            ).first()
            if existing:
                print(f"  [SKIP] Area '{a['short_code']}' ('{a['name']}') already exists (id={existing.id}).")
                stats["areas_skipped"] += 1
            else:
                area = Area(
                    name=a["name"],
                    short_code=a["short_code"],
                    ward_no=a["ward_no"],
                    color_name=a["color_name"],
                    color_hex=a["color_hex"],
                    landmark=a["landmark"],
                    animal_lover_name=a["animal_lover_name"],
                    animal_lover_phone=a["animal_lover_phone"],
                    last_dog_number=0,
                    is_active=True,
                )
                db.session.add(area)
                print(f"  [CREATE] Added area '{a['short_code']}' - '{a['name']}' ({a['color_name']} {a['color_hex']}).")
                stats["areas_created"] += 1

        # Commit all new records in one transaction
        db.session.commit()

        print("\n--- Seed Summary ---")
        print(f"Users : {stats['users_created']} created, {stats['users_skipped']} skipped")
        print(f"Areas : {stats['areas_created']} created, {stats['areas_skipped']} skipped")

    return stats


if __name__ == "__main__":
    seed_database()
