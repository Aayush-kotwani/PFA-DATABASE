"""Case model representing a rescue, surgery, and release episode."""

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class Case(db.Model, TimestampMixin, SoftDeleteMixin):
    """Case episode tracking pickup, medical procedure, prescription, and drop."""

    __tablename__ = "cases"

    id = db.Column(Integer, primary_key=True)
    dog_id = db.Column(Integer, ForeignKey("dogs.id"), nullable=False, index=True)

    pickup_date = db.Column(Date, nullable=False, index=True)
    pickup_location = db.Column(String(200), nullable=True)
    picked_by = db.Column(String(100), nullable=True)

    surgery_date = db.Column(Date, nullable=True, index=True)
    procedure = db.Column(String(100), nullable=True)
    surgeon_name = db.Column(String(100), nullable=True)
    pre_op_notes = db.Column(Text, nullable=True)
    post_op_notes = db.Column(Text, nullable=True)
    prescription_details = db.Column(Text, nullable=True)
    complications = db.Column(Text, nullable=True)

    drop_date = db.Column(Date, nullable=True, index=True)
    drop_location = db.Column(String(200), nullable=True)
    released_same_spot = db.Column(Boolean, nullable=True)

    # Structured analytics fields
    surgery_outcome = db.Column(
        Enum("success", "complication", "death", name="surgery_outcome_enum"),
        nullable=True,
    )
    complication_type = db.Column(String(100), nullable=True)
    recovery_days = db.Column(Integer, nullable=True)

    # Audit foreign keys
    created_by = db.Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = db.Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    dog = db.relationship("Dog", back_populates="cases")
    vaccinations = db.relationship("Vaccination", back_populates="case", lazy="select")
    photos = db.relationship("DogPhoto", back_populates="case", lazy="select")
    creator = db.relationship("User", foreign_keys=[created_by], backref="cases_created")
    updater = db.relationship("User", foreign_keys=[updated_by], backref="cases_updated")

    __table_args__ = (
        Index("ix_cases_pickup_date", "pickup_date"),
        Index("ix_cases_surgery_date", "surgery_date"),
        Index("ix_cases_drop_date", "drop_date"),
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} dog_id={self.dog_id} pickup='{self.pickup_date}'>"
