"""Vaccination model for tracking immunizations and upcoming due dates."""

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text
from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class Vaccination(db.Model, TimestampMixin, SoftDeleteMixin):
    """Vaccination administration record with next-due calculation."""

    __tablename__ = "vaccinations"

    id = db.Column(Integer, primary_key=True)
    dog_id = db.Column(Integer, ForeignKey("dogs.id"), nullable=False, index=True)
    case_id = db.Column(Integer, ForeignKey("cases.id"), nullable=True, index=True)

    vaccine_name = db.Column(String(100), nullable=False)
    date_given = db.Column(Date, nullable=False)
    batch_no = db.Column(String(50), nullable=True)
    next_due_date = db.Column(Date, nullable=True, index=True)
    given_by = db.Column(String(100), nullable=True)
    notes = db.Column(Text, nullable=True)

    created_by = db.Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    dog = db.relationship("Dog", back_populates="vaccinations")
    case = db.relationship("Case", back_populates="vaccinations")
    creator = db.relationship("User", foreign_keys=[created_by], backref="vaccinations_created")

    def __repr__(self) -> str:
        return (
            f"<Vaccination id={self.id} dog_id={self.dog_id} "
            f"vaccine='{self.vaccine_name}' given='{self.date_given}'>"
        )
