"""Create the first admin user in production via interactive hidden password prompt."""

import argparse
import getpass
import os
import sys
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.audit_service import log_audit  # noqa: E402

_WEAK_MARKERS = ("change-me", "changeme", "password", "admin123", "replace-with")


def validate_admin_password(password: str) -> None:
    """Enforce strong password rules without printing the password."""
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long.")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must include at least one uppercase letter.")
    if not any(c.islower() for c in password):
        raise ValueError("Password must include at least one lowercase letter.")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must include at least one digit.")
    lowered = password.lower()
    if any(marker in lowered for marker in _WEAK_MARKERS):
        raise ValueError("Password contains a forbidden placeholder or weak word.")


def create_first_admin(force: bool = False, app=None) -> User:
    """Prompt for password and create an admin user with an audit log entry."""
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    if not admin_email or "@" not in admin_email:
        raise ValueError("ADMIN_EMAIL environment variable must be set to a valid email.")

    admin_name = os.getenv("ADMIN_NAME", "NGO Admin").strip() or "NGO Admin"

    password = getpass.getpass("Enter new admin password (hidden): ")
    confirm = getpass.getpass("Confirm admin password (hidden): ")
    if password != confirm:
        raise ValueError("Passwords do not match.")
    validate_admin_password(password)

    flask_app = app or create_app()
    with flask_app.app_context():
        existing_admin = User.query.filter_by(role="admin").first()
        if existing_admin and not force:
            raise RuntimeError(
                "An admin account already exists. Re-run with --force to create another."
            )

        if User.query.filter_by(email=admin_email).first():
            raise RuntimeError(f"A user with email '{admin_email}' already exists.")

        user = User(
            name=admin_name,
            email=admin_email,
            password_hash=generate_password_hash(password),
            role="admin",
            is_active=True,
        )
        try:
            db.session.add(user)
            db.session.flush()
            log_audit(
                action="create",
                table_name="users",
                record_id=user.id,
                user_id=user.id,
                changes={
                    "name": user.name,
                    "email": user.email,
                    "role": "admin",
                    "source": "create_admin.py",
                },
            )
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise

        print(f"Created admin user id={user.id} email={user.email}")
        return user


def main() -> int:
    """CLI entry point for production admin creation."""
    parser = argparse.ArgumentParser(description="Create initial production admin user.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow creating an admin even if an admin already exists.",
    )
    args = parser.parse_args()

    try:
        create_first_admin(force=args.force)
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
