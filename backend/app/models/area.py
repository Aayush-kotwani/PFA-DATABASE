"""Area model representing geographic operational zones."""

from sqlalchemy import Boolean, Integer, String
from app.extensions import db
from app.models.mixins import TimestampMixin


class Area(db.Model, TimestampMixin):
    """Geographic operational area with unique color and dog counter."""

    __tablename__ = "areas"

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(120), nullable=False, unique=True)
    short_code = db.Column(String(10), nullable=False, unique=True)
    ward_no = db.Column(String(20), nullable=False)
    color_name = db.Column(String(30), nullable=False)
    color_hex = db.Column(String(7), nullable=False, unique=True)
    landmark = db.Column(String(200), nullable=True)
    animal_lover_name = db.Column(String(100), nullable=True)
    animal_lover_phone = db.Column(String(20), nullable=True)
    last_dog_number = db.Column(Integer, nullable=False, default=0)
    is_active = db.Column(Boolean, nullable=False, default=True)

    # Relationships
    dogs = db.relationship("Dog", back_populates="area", lazy="select")

    def __repr__(self) -> str:
        return f"<Area id={self.id} code='{self.short_code}' name='{self.name}'>"
