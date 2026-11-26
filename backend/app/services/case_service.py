"""Business logic services for Case management."""

from datetime import date
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.case import Case
from app.models.dog import Dog
from app.models.user import User
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


def _get_active_case(dog_id: int, case_id: int) -> Case:
    """Verify parent dog is active, then return non-deleted Case or raise 404."""
    _get_active_dog(dog_id)
    case = Case.query.filter(
        Case.id == case_id,
        Case.dog_id == dog_id,
        Case.is_deleted.is_(False),
    ).first()
    if not case:
        raise APIError(404, "NOT_FOUND", "Case not found")
    return case


def _validate_case_dates(
    pickup_date: date | None,
    surgery_date: date | None,
    drop_date: date | None,
) -> None:
    """Enforce chronological consistency across pickup, surgery, and drop dates."""
    if pickup_date and surgery_date and surgery_date < pickup_date:
        raise APIError(
            400, "INVALID_DATE_RANGE", "surgery_date cannot be earlier than pickup_date"
        )
    if pickup_date and drop_date and drop_date < pickup_date:
        raise APIError(
            400, "INVALID_DATE_RANGE", "drop_date cannot be earlier than pickup_date"
        )
    if surgery_date and drop_date and drop_date < surgery_date:
        raise APIError(
            400, "INVALID_DATE_RANGE", "drop_date cannot be earlier than surgery_date"
        )


def _sync_dog_status(dog: Dog, case: Case, actor_id: int) -> None:
    """Auto-advance dog.status based on case milestones without overwriting deceased/lost."""
    if dog.status in ("deceased", "lost"):
        return

    new_status = None
    if case.drop_date and dog.status in ("registered", "picked_up", "in_surgery", "recovering"):
        new_status = "released"
    elif case.surgery_date and dog.status in ("registered", "picked_up", "in_surgery"):
        new_status = "recovering"
    elif case.pickup_date and dog.status == "registered":
        new_status = "picked_up"

    if new_status and new_status != dog.status:
        dog.status = new_status
        dog.updated_by = actor_id


def list_cases(dog_id: int, page: int = 1, per_page: int = 20) -> dict[str, Any]:
    """Retrieve paginated list of non-deleted cases for a dog."""
    _get_active_dog(dog_id)
    query = Case.query.filter(
        Case.dog_id == dog_id, Case.is_deleted.is_(False)
    ).order_by(Case.pickup_date.desc(), Case.id.desc())
    return paginate_query(query, page=page, per_page=per_page)


def get_case(dog_id: int, case_id: int) -> Case:
    """Retrieve a single non-deleted case belonging to a dog."""
    return _get_active_case(dog_id, case_id)


def create_case(dog_id: int, data: dict[str, Any], actor: User) -> Case:
    """Create a new case episode under a dog with date validation and audit logging."""
    _get_active_dog(dog_id)
    _validate_case_dates(
        data.get("pickup_date"),
        data.get("surgery_date"),
        data.get("drop_date"),
    )

    recovery_days = data.get("recovery_days")
    if recovery_days is None and data.get("surgery_date") and data.get("drop_date"):
        recovery_days = (data["drop_date"] - data["surgery_date"]).days

    case = Case(
        dog_id=dog_id,
        pickup_date=data["pickup_date"],
        pickup_location=data.get("pickup_location"),
        picked_by=data.get("picked_by"),
        surgery_date=data.get("surgery_date"),
        procedure=data.get("procedure"),
        surgeon_name=data.get("surgeon_name"),
        surgery_outcome=data.get("surgery_outcome"),
        complication_type=data.get("complication_type"),
        recovery_days=recovery_days,
        pre_op_notes=data.get("pre_op_notes"),
        post_op_notes=data.get("post_op_notes"),
        prescription_details=data.get("prescription_details"),
        complications=data.get("complications"),
        drop_date=data.get("drop_date"),
        drop_location=data.get("drop_location"),
        released_same_spot=data.get("released_same_spot"),
        created_by=actor.id,
    )

    try:
        db.session.add(case)
        db.session.flush()
        _sync_dog_status(case.dog, case, actor.id)

        audit_changes: dict[str, Any] = {
            "dog_id": case.dog_id,
            "pickup_date": _to_json_safe(case.pickup_date),
        }
        if case.surgery_date:
            audit_changes["surgery_date"] = _to_json_safe(case.surgery_date)
        if case.drop_date:
            audit_changes["drop_date"] = _to_json_safe(case.drop_date)

        log_audit(
            action="create",
            table_name="cases",
            record_id=case.id,
            user_id=actor.id,
            changes=audit_changes,
        )
        db.session.commit()
        db.session.refresh(case)
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return case


def update_case(
    dog_id: int, case_id: int, data: dict[str, Any], actor: User
) -> Case:
    """Update case details, validating effective date ordering and recording audit diffs."""
    case = _get_active_case(dog_id, case_id)

    effective_pickup = data["pickup_date"] if "pickup_date" in data else case.pickup_date
    effective_surgery = data["surgery_date"] if "surgery_date" in data else case.surgery_date
    effective_drop = data["drop_date"] if "drop_date" in data else case.drop_date
    _validate_case_dates(effective_pickup, effective_surgery, effective_drop)

    # Auto-calculate recovery_days when omitted/None and both surgery_date & drop_date exist
    payload = dict(data)
    if payload.get("recovery_days") is None and effective_surgery and effective_drop:
        if case.recovery_days is None or "surgery_date" in payload or "drop_date" in payload or "recovery_days" in payload:
            payload["recovery_days"] = (effective_drop - effective_surgery).days

    editable_fields = [
        "pickup_date", "pickup_location", "picked_by",
        "surgery_date", "procedure", "surgeon_name",
        "surgery_outcome", "complication_type", "recovery_days",
        "pre_op_notes", "post_op_notes", "prescription_details", "complications",
        "drop_date", "drop_location", "released_same_spot",
    ]

    diff: dict[str, Any] = {}
    for field in editable_fields:
        if field in payload:
            old_val = _to_json_safe(getattr(case, field))
            new_val = _to_json_safe(payload[field])
            if isinstance(new_val, str):
                new_val = new_val.strip()
            if old_val != new_val:
                diff[field] = {"old": old_val, "new": new_val}
                setattr(case, field, payload[field].strip() if isinstance(payload[field], str) else payload[field])

    if diff:
        try:
            case.updated_by = actor.id
            _sync_dog_status(case.dog, case, actor.id)
            log_audit(
                action="update",
                table_name="cases",
                record_id=case.id,
                user_id=actor.id,
                changes=diff,
            )
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise

    return case


def soft_delete_case(dog_id: int, case_id: int, actor: User) -> dict[str, str]:
    """Soft-delete a case record (Admin only)."""
    case = _get_active_case(dog_id, case_id)

    try:
        case.soft_delete()
        case.updated_by = actor.id
        log_audit(
            action="delete",
            table_name="cases",
            record_id=case.id,
            user_id=actor.id,
            changes={"is_deleted": {"old": False, "new": True}},
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return {"message": "Case deleted successfully"}
