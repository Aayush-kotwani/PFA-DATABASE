"""Business logic services for Area management."""

from typing import Any
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.area import Area
from app.services.audit_service import log_audit
from app.utils.errors import APIError
from app.utils.pagination import paginate_query


def list_areas(page: int = 1, per_page: int = 20, is_active: bool | None = None) -> dict[str, Any]:
    """Retrieve paginated list of operational areas with optional is_active filter."""
    query = Area.query
    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    query = query.order_by(Area.id.asc())
    return paginate_query(query, page=page, per_page=per_page)


def get_area(area_id: int) -> Area:
    """Retrieve a single area by ID or raise 404."""
    area = db.session.get(Area, area_id)
    if not area:
        raise APIError(404, "NOT_FOUND", "Area not found")
    return area


def _validate_area_uniqueness(
    name: str | None = None,
    short_code: str | None = None,
    color_hex: str | None = None,
    exclude_area_id: int | None = None,
) -> None:
    """Validate uniqueness for area name (case-insensitive), short_code, and color_hex."""
    if name is not None:
        query = Area.query.filter(func.lower(Area.name) == name.strip().lower())
        if exclude_area_id:
            query = query.filter(Area.id != exclude_area_id)
        if query.first():
            raise APIError(409, "CONFLICT", f"An area with name '{name.strip()}' already exists")

    if short_code is not None:
        norm_code = short_code.strip().upper()
        query = Area.query.filter(func.upper(Area.short_code) == norm_code)
        if exclude_area_id:
            query = query.filter(Area.id != exclude_area_id)
        if query.first():
            raise APIError(409, "CONFLICT", f"An area with short code '{norm_code}' already exists")

    if color_hex is not None:
        norm_hex = color_hex.strip().upper()
        query = Area.query.filter(func.upper(Area.color_hex) == norm_hex)
        if exclude_area_id:
            query = query.filter(Area.id != exclude_area_id)
        if query.first():
            raise APIError(409, "CONFLICT", f"An area with color hex '{norm_hex}' already exists")


def create_area(data: dict[str, Any], actor_id: int) -> Area:
    """Create a new operational area after checking uniqueness across name, code, and color."""
    name = data["name"].strip()
    short_code = data["short_code"].strip().upper()
    color_hex = data["color_hex"].strip().upper()

    _validate_area_uniqueness(name=name, short_code=short_code, color_hex=color_hex)

    area = Area(
        name=name,
        short_code=short_code,
        ward_no=data["ward_no"].strip(),
        color_name=data["color_name"].strip(),
        color_hex=color_hex,
        landmark=data.get("landmark", "").strip() if data.get("landmark") else None,
        animal_lover_name=data.get("animal_lover_name", "").strip() if data.get("animal_lover_name") else None,
        animal_lover_phone=data.get("animal_lover_phone", "").strip() if data.get("animal_lover_phone") else None,
        last_dog_number=0,
        is_active=True,
    )

    try:
        db.session.add(area)
        db.session.flush()

        log_audit(
            action="create",
            table_name="areas",
            record_id=area.id,
            user_id=actor_id,
            changes={
                "name": area.name,
                "short_code": area.short_code,
                "ward_no": area.ward_no,
                "color_name": area.color_name,
                "color_hex": area.color_hex,
                "is_active": area.is_active,
            },
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return area


def update_area(area_id: int, data: dict[str, Any], actor_id: int) -> Area:
    """Update an area's fields with uniqueness validation and audit logging."""
    area = get_area(area_id)

    # Protect short_code from changing once dogs have been registered under this area
    if "short_code" in data and data["short_code"] is not None:
        new_short_code = data["short_code"].strip().upper()
        if area.last_dog_number > 0 and new_short_code != area.short_code:
            raise APIError(
                400,
                "BAD_REQUEST",
                "Cannot change short code for an area with registered dogs",
            )

    name = data.get("name")
    short_code = data.get("short_code")
    color_hex = data.get("color_hex")

    _validate_area_uniqueness(
        name=name.strip() if name else None,
        short_code=short_code.strip().upper() if short_code else None,
        color_hex=color_hex.strip().upper() if color_hex else None,
        exclude_area_id=area_id,
    )

    diff: dict[str, Any] = {}
    field_mappings = [
        "name", "short_code", "ward_no", "color_name", "color_hex",
        "landmark", "animal_lover_name", "animal_lover_phone", "is_active"
    ]

    for field in field_mappings:
        if field in data and data[field] is not None:
            old_val = getattr(area, field)
            new_val = data[field]
            if isinstance(new_val, str):
                new_val = new_val.strip()
                if field in ("short_code", "color_hex"):
                    new_val = new_val.upper()

            if old_val != new_val:
                diff[field] = {"old": old_val, "new": new_val}
                setattr(area, field, new_val)

    if diff:
        try:
            log_audit(
                action="update",
                table_name="areas",
                record_id=area.id,
                user_id=actor_id,
                changes=diff,
            )
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise

    return area


def deactivate_area(area_id: int, actor_id: int) -> Area:
    """Deactivate an area so it cannot be chosen for new dogs."""
    area = get_area(area_id)
    if not area.is_active:
        return area

    try:
        area.is_active = False
        log_audit(
            action="update",
            table_name="areas",
            record_id=area.id,
            user_id=actor_id,
            changes={"is_active": {"old": True, "new": False}},
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return area
