"""Schemas for Case management endpoints."""

from apiflask import Schema
from apiflask.fields import (
    Boolean,
    Date,
    DateTime,
    Integer,
    List,
    Nested,
    String,
)
from apiflask.validators import Length, OneOf, Range

SURGERY_OUTCOMES = ("success", "complication", "death")


class CaseOutSchema(Schema):
    """Response schema for a rescue/sterilization case episode."""

    id = Integer(required=True, metadata={"example": 1})
    dog_id = Integer(required=True, metadata={"example": 1})

    pickup_date = Date(required=True, metadata={"example": "2026-11-20"})
    pickup_location = String(allow_none=True, metadata={"example": "Clock Tower Gate"})
    picked_by = String(allow_none=True, metadata={"example": "NGO Volunteer"})

    surgery_date = Date(allow_none=True, metadata={"example": "2026-11-21"})
    procedure = String(allow_none=True, metadata={"example": "Ovariohysterectomy (Spay)"})
    surgeon_name = String(allow_none=True, metadata={"example": "Dr. Meera Nair"})
    surgery_outcome = String(allow_none=True, metadata={"example": "success"})
    complication_type = String(allow_none=True)
    recovery_days = Integer(allow_none=True, metadata={"example": 4})

    pre_op_notes = String(allow_none=True)
    post_op_notes = String(allow_none=True)
    prescription_details = String(allow_none=True)
    complications = String(allow_none=True)

    drop_date = Date(allow_none=True, metadata={"example": "2026-11-25"})
    drop_location = String(allow_none=True, metadata={"example": "Clock Tower Gate"})
    released_same_spot = Boolean(allow_none=True, metadata={"example": True})

    created_by = Integer(required=True)
    updated_by = Integer(allow_none=True)
    created_at = DateTime(required=True)
    updated_at = DateTime(required=True)


class CaseListOutSchema(Schema):
    """Paginated list response for cases under a dog."""

    items = List(Nested(CaseOutSchema), required=True)
    page = Integer(required=True, metadata={"example": 1})
    per_page = Integer(required=True, metadata={"example": 20})
    total = Integer(required=True, metadata={"example": 1})


class CaseCreateInSchema(Schema):
    """Payload schema for creating a new case under a dog."""

    pickup_date = Date(required=True, metadata={"example": "2026-11-20"})
    pickup_location = String(required=False, allow_none=True, validate=Length(max=200))
    picked_by = String(required=False, allow_none=True, validate=Length(max=100))

    surgery_date = Date(required=False, allow_none=True)
    procedure = String(required=False, allow_none=True, validate=Length(max=100))
    surgeon_name = String(required=False, allow_none=True, validate=Length(max=100))
    surgery_outcome = String(required=False, allow_none=True, validate=OneOf(SURGERY_OUTCOMES))
    complication_type = String(required=False, allow_none=True, validate=Length(max=100))
    recovery_days = Integer(required=False, allow_none=True, validate=Range(min=0, max=365))

    pre_op_notes = String(required=False, allow_none=True)
    post_op_notes = String(required=False, allow_none=True)
    prescription_details = String(required=False, allow_none=True)
    complications = String(required=False, allow_none=True)

    drop_date = Date(required=False, allow_none=True)
    drop_location = String(required=False, allow_none=True, validate=Length(max=200))
    released_same_spot = Boolean(required=False, allow_none=True)


class CaseUpdateInSchema(Schema):
    """Payload schema for updating an existing case."""

    pickup_date = Date(required=False)
    pickup_location = String(required=False, allow_none=True, validate=Length(max=200))
    picked_by = String(required=False, allow_none=True, validate=Length(max=100))

    surgery_date = Date(required=False, allow_none=True)
    procedure = String(required=False, allow_none=True, validate=Length(max=100))
    surgeon_name = String(required=False, allow_none=True, validate=Length(max=100))
    surgery_outcome = String(required=False, allow_none=True, validate=OneOf(SURGERY_OUTCOMES))
    complication_type = String(required=False, allow_none=True, validate=Length(max=100))
    recovery_days = Integer(required=False, allow_none=True, validate=Range(min=0, max=365))

    pre_op_notes = String(required=False, allow_none=True)
    post_op_notes = String(required=False, allow_none=True)
    prescription_details = String(required=False, allow_none=True)
    complications = String(required=False, allow_none=True)

    drop_date = Date(required=False, allow_none=True)
    drop_location = String(required=False, allow_none=True, validate=Length(max=200))
    released_same_spot = Boolean(required=False, allow_none=True)


class CaseMessageOutSchema(Schema):
    """Standard message response for case deletion."""

    message = String(required=True, metadata={"example": "Case deleted successfully"})
