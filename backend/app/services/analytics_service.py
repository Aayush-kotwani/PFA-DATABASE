"""Flat analytics dataset export service (CSV streaming & JSON)."""

import csv
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from typing import Any, Generator

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.case import Case
from app.models.dog import Dog
from app.models.vaccination import Vaccination

BASE_COLUMNS = [
    "dog_id", "dog_code", "area_name", "area_short_code", "ward_no",
    "area_color_name", "sex", "approx_age", "age_group", "weight_kg",
    "body_condition", "is_pregnant", "ear_notch_done", "status", "landmark",
    "created_at", "latest_pickup_date", "latest_surgery_date",
    "latest_procedure", "latest_surgery_outcome", "latest_complication_type",
    "latest_recovery_days", "latest_drop_date", "sterilized", "vaccination_count",
]

PERSONAL_COLUMNS = [
    "guardian_name", "guardian_phone", "capture_address",
    "latitude", "longitude", "maps_url",
]


def _serialize_val(val: Any) -> Any:
    """Convert dates, datetimes, and Decimals into JSON/CSV-safe primitives."""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    return val


def build_analytics_rows(
    include_personal: bool = False,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Build flat joined analytics rows (one row per active dog) without pagination cap."""
    dogs = (
        Dog.query.options(joinedload(Dog.area))
        .filter(Dog.is_deleted.is_(False))
        .order_by(Dog.id.asc())
        .all()
    )

    # Preload non-deleted cases ordered newest-first to avoid N+1 queries
    cases = (
        Case.query.filter(Case.is_deleted.is_(False))
        .order_by(Case.pickup_date.desc(), Case.id.desc())
        .all()
    )
    latest_case_by_dog: dict[int, Case] = {}
    sterilized_dog_ids: set[int] = set()
    for c in cases:
        if c.dog_id not in latest_case_by_dog:
            latest_case_by_dog[c.dog_id] = c
        if c.surgery_date is not None:
            sterilized_dog_ids.add(c.dog_id)

    vax_counts = dict(
        db.session.query(Vaccination.dog_id, func.count(Vaccination.id))
        .filter(Vaccination.is_deleted.is_(False))
        .group_by(Vaccination.dog_id)
        .all()
    )

    columns = list(BASE_COLUMNS) + (list(PERSONAL_COLUMNS) if include_personal else [])
    rows: list[dict[str, Any]] = []

    for dog in dogs:
        latest = latest_case_by_dog.get(dog.id)
        row: dict[str, Any] = {
            "dog_id": dog.id,
            "dog_code": dog.dog_code,
            "area_name": dog.area.name,
            "area_short_code": dog.area.short_code,
            "ward_no": dog.area.ward_no,
            "area_color_name": dog.area.color_name,
            "sex": dog.sex,
            "approx_age": dog.approx_age,
            "age_group": dog.age_group,
            "weight_kg": _serialize_val(dog.weight_kg),
            "body_condition": dog.body_condition,
            "is_pregnant": dog.is_pregnant,
            "ear_notch_done": dog.ear_notch_done,
            "status": dog.status,
            "landmark": dog.landmark,
            "created_at": _serialize_val(dog.created_at),
            "latest_pickup_date": _serialize_val(latest.pickup_date) if latest else None,
            "latest_surgery_date": _serialize_val(latest.surgery_date) if latest else None,
            "latest_procedure": latest.procedure if latest else None,
            "latest_surgery_outcome": latest.surgery_outcome if latest else None,
            "latest_complication_type": latest.complication_type if latest else None,
            "latest_recovery_days": latest.recovery_days if latest else None,
            "latest_drop_date": _serialize_val(latest.drop_date) if latest else None,
            "sterilized": dog.id in sterilized_dog_ids,
            "vaccination_count": vax_counts.get(dog.id, 0),
        }
        if include_personal:
            row.update(
                {
                    "guardian_name": dog.guardian_name,
                    "guardian_phone": dog.guardian_phone,
                    "capture_address": dog.capture_address,
                    "latitude": _serialize_val(dog.latitude),
                    "longitude": _serialize_val(dog.longitude),
                    "maps_url": dog.maps_url,
                }
            )
        rows.append(row)

    return columns, rows


def stream_analytics_csv(
    columns: list[str], rows: list[dict[str, Any]]
) -> Generator[str, None, None]:
    """Yield CSV header and rows incrementally for memory-efficient streaming."""
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    yield buf.getvalue()

    for row in rows:
        buf.seek(0)
        buf.truncate(0)
        writer.writerow(row)
        yield buf.getvalue()
