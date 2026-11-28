"""User model for authentication and role-based permissions."""

from sqlalchemy import Boolean, Enum, Integer, String, text
from app.extensions import db
from app.models.mixins import TimestampMixin


class User(db.Model, TimestampMixin):
    """User account with role (admin or volunteer)."""

    __tablename__ = "users"

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(100), nullable=False)
    email = db.Column(String(120), nullable=False, unique=True, index=True)
    password_hash = db.Column(String(255), nullable=False)
    role = db.Column(
        Enum("admin", "volunteer", name="user_role_enum"),
        nullable=False,
        default="volunteer",
    )
    is_active = db.Column(Boolean, nullable=False, default=True)
    token_version = db.Column(Integer, nullable=False, default=0, server_default=text("0"))

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
