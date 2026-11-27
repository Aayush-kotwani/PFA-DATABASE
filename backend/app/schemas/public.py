"""Schemas for public unauthenticated dog verification endpoint."""

from apiflask import Schema
from apiflask.fields import Boolean, Date, Nested, String


class PublicVaccinationSchema(Schema):
    """Minimal vaccination summary exposed on the public QR page."""

    vaccine_name = String(required=True, metadata={"example": "Anti-Rabies"})
    date_given = Date(required=True, metadata={"example": "2026-11-20"})


class PublicDogOutSchema(Schema):
    """Strictly allow-listed public dog profile (zero PII, medical, or GPS fields)."""

    dog_code = String(required=True, metadata={"example": "CTR-0001"})
    area_name = String(required=True, metadata={"example": "Central Zone - Ward 1"})
    area_color_name = String(required=True, metadata={"example": "Teal"})
    area_color_hex = String(required=True, metadata={"example": "#0D9488"})
    primary_photo_url = String(allow_none=True)
    sterilized = Boolean(required=True, metadata={"example": True})
    latest_vaccination = Nested(PublicVaccinationSchema, allow_none=True)
    ngo_contact = String(
        required=True,
        metadata={"example": "Animal Welfare NGO Helpline: +91-00000-00000"},
    )
