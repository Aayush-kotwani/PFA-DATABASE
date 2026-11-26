"""Business logic services for Vaccination management."""

from datetime import date, timedelta
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.area import Area
from app.models.case import Case
from app.models.dog import Dog
from app.models.user import User
from app.models.vaccination import Vaccination
from app.services.audit_service import log_audit
from app.utils.errors import APIError
from app.utils.pagination import paginate_query


def _to_json_safe(val: Any) -> Any:
    """Convert date objects to ISO strings for JSONB audit logging."""
    return val.isoformat() if isinstance(val, date) else val


def _get_active_dog(dog_id: int) -> Dog:
    """Return a non-deleted Dog by ID or raise 404."""
    dog = Dog.query.filter(Dog.id == dog_id, Dog.is_deleted.is_(False)).first()
    if not dog:
        raise APIError(404, "NOT_FOUND", "Dog not found")
    return dog


def _get_active_vaccination(dog_id: int, vaccination_id: int) -> Vaccination:
    """Verify parent dog is active, then return non-deleted Vaccination or raise 404."""
    _get_active_dog(dog_id)
    vaccination = Vaccination.query.filter(
        Vaccination.id == vaccination_id,
        Vaccination.dog_id == dog_id,
        Vaccination.is_deleted.is_(False),
    ).first()
    if not vaccination:
        raise APIError(404, "NOT_FOUND", "Vaccination not found")
    return vaccination


def _validate_case_link(dog_id: int, case_id: int | None) -> None:
    """Ensure optional case_id belongs to the given dog and is not soft-deleted."""
    if case_id is None:
        return
    case = Case.query.filter(
        Case.id == case_id,
        Case.dog_id == dog_id,
        Case.is_deleted.is_(False),
    ).first()
    if not case:
        raise APIError(400, "INVALID_CASE", "Case not found for this dog")


def _validate_dates(date_given: date | None, next_due_date: date | None) -> None:
    """Ensure next_due_date is not earlier than date_given."""
    if date_given and next_due_date and next_due_date < date_given:
        raise APIError(
            400,
            "INVALID_DATE_RANGE",
            "next_due_date cannot be earlier than date_given",
        )


def list_vaccinations(dog_id: int, page: int = 1, per_page: int = 20) -> dict[str, Any]:
    """Retrieve paginated list of non-deleted vaccinations for a dog."""
    _get_active_dog(dog_id)
    query = Vaccination.query.filter(
        Vaccination.dog_id == dog_id,
        Vaccination.is_deleted.is_(False),
    ).order_by(Vaccination.date_given.desc(), Vaccination.id.desc())
    return paginate_query(query, page=page, per_page=per_page)


def get_vaccination(dog_id: int, vaccination_id: int) -> Vaccination:
    """Retrieve a single non-deleted vaccination belonging to a dog."""
    return _get_active_vaccination(dog_id, vaccination_id)


def create_vaccination(dog_id: int, data: dict[str, Any], actor: User) -> Vaccination:
    """Record a new vaccination under a dog with validation and audit logging."""
    _get_active_dog(dog_id)
    _validate_case_link(dog_id, data.get("case_id"))
    _validate_dates(data.get("date_given"), data.get("next_due_date"))

    vaccination = Vaccination(
        dog_id=dog_id,
        case_id=data.get("case_id"),
        vaccine_name=data["vaccine_name"].strip(),
        date_given=data["date_given"],
        batch_no=data.get("batch_no"),
        next_due_date=data.get("next_due_date"),
        given_by=data.get("given_by"),
        notes=data.get("notes"),
        created_by=actor.id,
    )

    try:
        db.session.add(vaccination)
        db.session.flush()

        audit_changes: dict[str, Any] = {
            "dog_id": vaccination.dog_id,
            "vaccine_name": vaccination.vaccine_name,
            "date_given": _to_json_safe(vaccination.date_given),
        }
        if vaccination.next_due_date:
            audit_changes["next_due_date"] = _to_json_safe(vaccination.next_due_date)
        if vaccination.case_id is not None:
            audit_changes["case_id"] = vaccination.case_id

        log_audit(
            action="create",
            table_name="vaccinations",
            record_id=vaccination.id,
            user_id=actor.id,
            changes=audit_changes,
        )
        db.session.commit()
        db.session.refresh(vaccination)
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return vaccination


def update_vaccination(
    dog_id: int, vaccination_id: int, data: dict[str, Any], actor: User
) -> Vaccination:
    """Update a vaccination record, validating case link and date ordering."""
    vaccination = _get_active_vaccination(dog_id, vaccination_id)

    if "case_id" in data and data["case_id"] != vaccination.case_id:
        _validate_case_link(dog_id, data["case_id"])

    effective_given = data["date_given"] if "date_given" in data else vaccination.date_given
    effective_due = data["next_due_date"] if "next_due_date" in data else vaccination.next_due_date
    _validate_dates(effective_given, effective_due)

    editable_fields = [
        "case_id",
        "vaccine_name",
        "date_given",
        "batch_no",
        "next_due_date",
        "given_by",
        "notes",
    ]

    diff: dict[str, Any] = {}
    for field in editable_fields:
        if field in data:
            old_val = _to_json_safe(getattr(vaccination, field))
            raw_new = data[field].strip() if isinstance(data[field], str) else data[field]
            new_val = _to_json_safe(raw_new)
            if old_val != new_val:
                diff[field] = {"old": old_val, "new": new_val}
                setattr(vaccination, field, raw_new)

    if diff:
        try:
            log_audit(
                action="update",
                table_name="vaccinations",
                record_id=vaccination.id,
                user_id=actor.id,
                changes=diff,
            )
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise

    return vaccination


def soft_delete_vaccination(dog_id: int, vaccination_id: int, actor: User) -> dict[str, str]:
    """Soft-delete a vaccination record (Admin only)."""
    vaccination = _get_active_vaccination(dog_id, vaccination_id)

    try:
        vaccination.soft_delete()
        log_audit(
            action="delete",
            table_name="vaccinations",
            record_id=vaccination.id,
            user_id=actor.id,
            changes={"is_deleted": {"old": False, "new": True}},
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return {"message": "Vaccination deleted successfully"}


def get_due_vaccinations(days: int = 30) -> dict[str, Any]:
    """Return overdue and upcoming vaccinations within the next `days` days."""
    today = date.today()
    cutoff = today + timedelta(days=days)

    rows = (
        db.session.query(Vaccination, Dog, Area)
        .join(Dog, Vaccination.dog_id == Dog.id)
        .join(Area, Dog.area_id == Area.id)
        .filter(
            Vaccination.is_deleted.is_(False),
            Dog.is_deleted.is_(False),
            Vaccination.next_due_date.isnot(None),
            Vaccination.next_due_date <= cutoff,
        )
        .order_by(Vaccination.next_due_date.asc(), Vaccination.id.asc())
        .all()
    )

    overdue: list[dict[str, Any]] = []
    upcoming: list[dict[str, Any]] = []

    for vax, dog, area in rows:
        days_until_due = (vax.next_due_date - today).days
        item = {
            "id": vax.id,
            "dog_id": dog.id,
            "dog_code": dog.dog_code,
            "area_name": area.name,
            "area_color_hex": area.color_hex,
            "case_id": vax.case_id,
            "vaccine_name": vax.vaccine_name,
            "date_given": vax.date_given,
            "next_due_date": vax.next_due_date,
            "days_until_due": days_until_due,
            "given_by": vax.given_by,
        }
        if days_until_due < 0:
            overdue.append(item)
        else:
            upcoming.append(item)

    return {
        "days": days,
        "as_of": today,
        "overdue": overdue,
        "upcoming": upcoming,
    }
