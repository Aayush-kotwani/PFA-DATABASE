"""Business logic service for Dashboard operational statistics."""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, extract, func

from app.extensions import db
from app.models.area import Area
from app.models.case import Case
from app.models.dog import Dog
from app.models.vaccination import Vaccination
from app.schemas.dog import DOG_STATUSES


def get_dashboard_stats() -> dict[str, Any]:
    """Compute live operational statistics excluding soft-deleted records."""
    today = date.today()
    upcoming_cutoff = today + timedelta(days=30)

    total_dogs = Dog.query.filter(Dog.is_deleted.is_(False)).count()

    # Initialize all known statuses to 0 so frontend charts always receive every key
    by_status: dict[str, int] = {status: 0 for status in DOG_STATUSES}
    status_rows = (
        db.session.query(Dog.status, func.count(Dog.id))
        .filter(Dog.is_deleted.is_(False))
        .group_by(Dog.status)
        .all()
    )
    for status_name, count in status_rows:
        by_status[status_name] = count

    area_rows = (
        db.session.query(
            Area.id,
            Area.name,
            Area.short_code,
            Area.color_hex,
            func.count(Dog.id),
        )
        .outerjoin(Dog, and_(Dog.area_id == Area.id, Dog.is_deleted.is_(False)))
        .group_by(Area.id)
        .order_by(Area.id.asc())
        .all()
    )
    by_area = [
        {
            "area_id": row[0],
            "area_name": row[1],
            "short_code": row[2],
            "color_hex": row[3],
            "count": row[4],
        }
        for row in area_rows
    ]

    sterilized_this_month = (
        db.session.query(func.count(func.distinct(Case.dog_id)))
        .join(Dog, Case.dog_id == Dog.id)
        .filter(
            Case.is_deleted.is_(False),
            Dog.is_deleted.is_(False),
            Case.surgery_date.isnot(None),
            extract("year", Case.surgery_date) == today.year,
            extract("month", Case.surgery_date) == today.month,
        )
        .scalar()
        or 0
    )

    overdue_count = (
        db.session.query(func.count(Vaccination.id))
        .join(Dog, Vaccination.dog_id == Dog.id)
        .filter(
            Vaccination.is_deleted.is_(False),
            Dog.is_deleted.is_(False),
            Vaccination.next_due_date.isnot(None),
            Vaccination.next_due_date < today,
        )
        .scalar()
        or 0
    )

    upcoming_count = (
        db.session.query(func.count(Vaccination.id))
        .join(Dog, Vaccination.dog_id == Dog.id)
        .filter(
            Vaccination.is_deleted.is_(False),
            Dog.is_deleted.is_(False),
            Vaccination.next_due_date.isnot(None),
            Vaccination.next_due_date >= today,
            Vaccination.next_due_date <= upcoming_cutoff,
        )
        .scalar()
        or 0
    )

    return {
        "total_dogs": total_dogs,
        "by_status": by_status,
        "by_area": by_area,
        "sterilized_this_month": sterilized_this_month,
        "vaccinations_due": {
            "overdue": overdue_count,
            "upcoming_30_days": upcoming_count,
        },
    }
