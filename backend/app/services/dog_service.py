"""Business logic services for Dog management."""

from datetime import datetime, time, timezone
from decimal import Decimal
import secrets
from typing import Any

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.area import Area
from app.models.dog import Dog
from app.models.user import User
from app.services.audit_service import log_audit
from app.utils.errors import APIError
from app.utils.pagination import paginate_query


def _to_json_safe(val: Any) -> Any:
    """Convert Decimal values to float so audit diff payloads serialize cleanly to JSONB."""
    return float(val) if isinstance(val, Decimal) else val


def list_dogs(filters: dict[str, Any]) -> dict[str, Any]:
    """Retrieve paginated list of non-deleted dogs with search and filters."""
    query = Dog.query.options(joinedload(Dog.area)).filter(Dog.is_deleted.is_(False))

    search = filters.get("search")
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Dog.dog_code.ilike(term),
                Dog.guardian_name.ilike(term),
                Dog.landmark.ilike(term),
            )
        )

    if filters.get("area_id") is not None:
        query = query.filter(Dog.area_id == filters["area_id"])
    if filters.get("status"):
        query = query.filter(Dog.status == filters["status"])
    if filters.get("sex"):
        query = query.filter(Dog.sex == filters["sex"])

    if filters.get("created_from"):
        start_dt = datetime.combine(filters["created_from"], time.min, tzinfo=timezone.utc)
        query = query.filter(Dog.created_at >= start_dt)
    if filters.get("created_to"):
        end_dt = datetime.combine(filters["created_to"], time.max, tzinfo=timezone.utc)
        query = query.filter(Dog.created_at <= end_dt)

    query = query.order_by(Dog.id.desc())
    return paginate_query(
        query,
        page=filters.get("page", 1),
        per_page=filters.get("per_page", 20),
    )


def get_dog(dog_id: int) -> Dog:
    """Retrieve a single non-deleted dog by ID or raise 404."""
    dog = (
        Dog.query.options(joinedload(Dog.area))
        .filter(Dog.id == dog_id, Dog.is_deleted.is_(False))
        .first()
    )
    if not dog:
        raise APIError(404, "NOT_FOUND", "Dog not found")
    return dog


def create_dog(data: dict[str, Any], actor: User) -> Dog:
    """Register a new dog with atomic row-locked dog_code generation."""
    try:
        # Row-level lock prevents duplicate dog_code under concurrent requests
        area = Area.query.filter_by(id=data["area_id"]).with_for_update().first()
        if not area:
            raise APIError(404, "NOT_FOUND", "Area not found")
        if not area.is_active:
            raise APIError(400, "BAD_REQUEST", "Cannot register a dog in an inactive area")

        area.last_dog_number += 1
        dog_code = f"{area.short_code}-{area.last_dog_number:04d}"

        dog = Dog(
            dog_code=dog_code,
            public_token=secrets.token_urlsafe(32),
            area_id=area.id,
            sex=data.get("sex", "unknown"),
            approx_age=data.get("approx_age"),
            age_group=data.get("age_group"),
            coat_description=data.get("coat_description"),
            weight_kg=data.get("weight_kg"),
            body_condition=data.get("body_condition"),
            is_pregnant=data.get("is_pregnant"),
            temperament=data.get("temperament"),
            guardian_name=data.get("guardian_name"),
            guardian_phone=data.get("guardian_phone"),
            capture_address=data.get("capture_address"),
            landmark=data.get("landmark"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            ear_notch_done=data.get("ear_notch_done", False),
            status=data.get("status", "registered"),
            medical_conditions=data.get("medical_conditions"),
            medical_history=data.get("medical_history"),
            created_by=actor.id,
        )
        db.session.add(dog)
        db.session.flush()

        audit_changes: dict[str, Any] = {
            "dog_code": dog.dog_code,
            "area_id": dog.area_id,
            "sex": dog.sex,
            "status": dog.status,
        }
        # Never store plaintext guardian_phone in audit logs
        if dog.guardian_phone:
            audit_changes["guardian_phone"] = {"provided": True}

        log_audit(
            action="create",
            table_name="dogs",
            record_id=dog.id,
            user_id=actor.id,
            changes=audit_changes,
        )
        db.session.commit()
        db.session.refresh(dog)
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return dog


def update_dog(dog_id: int, data: dict[str, Any], actor: User) -> Dog:
    """Update dog details; volunteers cannot overwrite guardian_phone."""
    dog = get_dog(dog_id)

    editable_fields = [
        "sex", "approx_age", "age_group", "coat_description", "weight_kg",
        "body_condition", "is_pregnant", "temperament", "guardian_name",
        "capture_address", "landmark", "latitude", "longitude",
        "ear_notch_done", "status", "medical_conditions", "medical_history",
    ]
    # Only admins may update guardian_phone; volunteers' guardian_phone input is silently ignored
    if actor.role == "admin":
        editable_fields.append("guardian_phone")

    diff: dict[str, Any] = {}
    for field in editable_fields:
        if field in data:
            old_val = _to_json_safe(getattr(dog, field))
            new_val = _to_json_safe(data[field])
            if isinstance(new_val, str):
                new_val = new_val.strip()
            if old_val != new_val:
                # Never store plaintext guardian_phone in audit logs
                if field == "guardian_phone":
                    diff[field] = {"updated": True}
                else:
                    diff[field] = {"old": old_val, "new": new_val}
                setattr(dog, field, new_val)

    if diff:
        try:
            dog.updated_by = actor.id
            log_audit(
                action="update",
                table_name="dogs",
                record_id=dog.id,
                user_id=actor.id,
                changes=diff,
            )
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise

    return dog


def delete_dog(dog_id: int, actor: User) -> dict[str, str]:
    """Soft-delete a dog record (Admin only)."""
    dog = get_dog(dog_id)

    try:
        dog.soft_delete()
        dog.updated_by = actor.id
        log_audit(
            action="delete",
            table_name="dogs",
            record_id=dog.id,
            user_id=actor.id,
            changes={"is_deleted": {"old": False, "new": True}},
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return {"message": "Dog deleted successfully"}
