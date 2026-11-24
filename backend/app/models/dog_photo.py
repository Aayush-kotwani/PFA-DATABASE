"""Dog photo model for media tracking and primary photo designation."""

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class DogPhoto(db.Model, TimestampMixin, SoftDeleteMixin):
    """Photo metadata pointing to a storage key with photo type and primary flag."""

    __tablename__ = "dog_photos"

    id = db.Column(Integer, primary_key=True)
    dog_id = db.Column(Integer, ForeignKey("dogs.id"), nullable=False, index=True)
    case_id = db.Column(Integer, ForeignKey("cases.id"), nullable=True, index=True)

    storage_key = db.Column(String(255), nullable=False)
    photo_type = db.Column(
        Enum("intake", "post_surgery", "release", "other", name="photo_type_enum"),
        nullable=False,
        default="intake",
    )
    is_primary = db.Column(Boolean, nullable=False, default=False)

    uploaded_by = db.Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    dog = db.relationship("Dog", back_populates="photos")
    case = db.relationship("Case", back_populates="photos")
    uploader = db.relationship("User", foreign_keys=[uploaded_by], backref="photos_uploaded")

    def __repr__(self) -> str:
        return (
            f"<DogPhoto id={self.id} dog_id={self.dog_id} "
            f"type='{self.photo_type}' primary={self.is_primary}>"
        )
