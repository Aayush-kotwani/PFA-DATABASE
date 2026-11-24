"""Dog model representing an animal profile and rescue identity."""

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class Dog(db.Model, TimestampMixin, SoftDeleteMixin):
    """Dog entity with identity, capture location, status, and health fields."""

    __tablename__ = "dogs"

    id = db.Column(Integer, primary_key=True)
    dog_code = db.Column(String(30), nullable=False, unique=True, index=True)
    public_token = db.Column(String(64), nullable=False, unique=True, index=True)
    area_id = db.Column(Integer, ForeignKey("areas.id"), nullable=False, index=True)

    sex = db.Column(
        Enum("male", "female", "unknown", name="dog_sex_enum"),
        nullable=False,
        default="unknown",
    )
    approx_age = db.Column(String(30), nullable=True)
    coat_description = db.Column(String(200), nullable=True)
    weight_kg = db.Column(Numeric(5, 2), nullable=True)
    temperament = db.Column(Text, nullable=True)

    # Guardian contact details (phone is strictly ADMIN-read-only in API responses)
    guardian_name = db.Column(String(100), nullable=True)
    guardian_phone = db.Column(String(20), nullable=True)

    # Location fields
    capture_address = db.Column(Text, nullable=True)
    landmark = db.Column(String(200), nullable=True)
    latitude = db.Column(Numeric(9, 6), nullable=True)
    longitude = db.Column(Numeric(9, 6), nullable=True)

    ear_notch_done = db.Column(Boolean, nullable=False, default=False)
    status = db.Column(
        Enum(
            "registered",
            "picked_up",
            "in_surgery",
            "recovering",
            "released",
            "deceased",
            "lost",
            name="dog_status_enum",
        ),
        nullable=False,
        default="registered",
        index=True,
    )

    # Free-text medical notes
    medical_conditions = db.Column(Text, nullable=True)
    medical_history = db.Column(Text, nullable=True)

    # Structured analytics fields (nullable so they never block data entry)
    age_group = db.Column(
        Enum("puppy", "young", "adult", "senior", name="dog_age_group_enum"),
        nullable=True,
    )
    body_condition = db.Column(
        Enum(
            "underweight",
            "normal",
            "overweight",
            name="dog_body_condition_enum",
        ),
        nullable=True,
    )
    is_pregnant = db.Column(Boolean, nullable=True)

    # Audit user foreign keys
    created_by = db.Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = db.Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    area = db.relationship("Area", back_populates="dogs")
    cases = db.relationship(
        "Case",
        back_populates="dog",
        cascade="all, delete-orphan",
        order_by="Case.pickup_date.desc()",
    )
    vaccinations = db.relationship(
        "Vaccination",
        back_populates="dog",
        cascade="all, delete-orphan",
        order_by="Vaccination.date_given.desc()",
    )
    photos = db.relationship(
        "DogPhoto",
        back_populates="dog",
        cascade="all, delete-orphan",
    )
    creator = db.relationship("User", foreign_keys=[created_by], backref="dogs_created")
    updater = db.relationship("User", foreign_keys=[updated_by], backref="dogs_updated")

    __table_args__ = (
        Index("ix_dogs_created_at", "created_at"),
    )

    @property
    def maps_url(self) -> str | None:
        """Compute Google Maps search URL from coordinates if both are present."""
        if self.latitude is not None and self.longitude is not None:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return None

    def __repr__(self) -> str:
        return f"<Dog id={self.id} code='{self.dog_code}' status='{self.status}'>"
