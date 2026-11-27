"""Business logic services for dog QR code generation and public info lookup."""

from io import BytesIO
from typing import Any

from flask import current_app
import qrcode
from sqlalchemy.orm import joinedload

from app.models.case import Case
from app.models.dog import Dog
from app.models.dog_photo import DogPhoto
from app.models.vaccination import Vaccination
from app.services.storage import get_storage
from app.utils.errors import APIError


def generate_dog_qr_png(dog_id: int) -> tuple[bytes, str]:
    """Generate a QR code PNG encoding the public verification URL for a dog."""
    dog = Dog.query.filter(Dog.id == dog_id, Dog.is_deleted.is_(False)).first()
    if not dog:
        raise APIError(404, "NOT_FOUND", "Dog not found")

    qr_url = f"{current_app.config['PUBLIC_BASE_URL']}/d/{dog.public_token}"
    qr_img = qrcode.make(qr_url)

    buf = BytesIO()
    qr_img.save(buf, format="PNG")
    return buf.getvalue(), dog.dog_code


def get_public_dog_info(public_token: str) -> dict[str, Any]:
    """Return strictly allow-listed public info for a non-deleted dog by public_token."""
    dog = (
        Dog.query.options(joinedload(Dog.area))
        .filter(Dog.public_token == public_token, Dog.is_deleted.is_(False))
        .first()
    )
    if not dog:
        raise APIError(404, "NOT_FOUND", "Dog not found")

    primary_photo = DogPhoto.query.filter(
        DogPhoto.dog_id == dog.id,
        DogPhoto.is_deleted.is_(False),
        DogPhoto.is_primary.is_(True),
    ).first()
    primary_photo_url = (
        get_storage().get_url(primary_photo.storage_key) if primary_photo else None
    )

    sterilized = (
        Case.query.filter(
            Case.dog_id == dog.id,
            Case.is_deleted.is_(False),
            Case.surgery_date.isnot(None),
        ).first()
        is not None
    )

    latest_vax = (
        Vaccination.query.filter(
            Vaccination.dog_id == dog.id,
            Vaccination.is_deleted.is_(False),
        )
        .order_by(Vaccination.date_given.desc(), Vaccination.id.desc())
        .first()
    )
    latest_vaccination = (
        {
            "vaccine_name": latest_vax.vaccine_name,
            "date_given": latest_vax.date_given,
        }
        if latest_vax
        else None
    )

    return {
        "dog_code": dog.dog_code,
        "area_name": dog.area.name,
        "area_color_name": dog.area.color_name,
        "area_color_hex": dog.area.color_hex,
        "primary_photo_url": primary_photo_url,
        "sterilized": sterilized,
        "latest_vaccination": latest_vaccination,
        "ngo_contact": current_app.config["NGO_CONTACT_TEXT"],
    }
