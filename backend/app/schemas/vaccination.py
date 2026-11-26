"""Schemas for Vaccination management and due-date tracking endpoints."""

from apiflask import Schema
from apiflask.fields import Date, DateTime, Integer, List, Nested, String
from apiflask.validators import Length, Range


class VaccinationOutSchema(Schema):
    """Response schema for a vaccination record."""

    id = Integer(required=True, metadata={"example": 1})
    dog_id = Integer(required=True, metadata={"example": 1})
    case_id = Integer(allow_none=True, metadata={"example": 1})

    vaccine_name = String(required=True, metadata={"example": "Anti-Rabies"})
    date_given = Date(required=True, metadata={"example": "2026-11-01"})
    batch_no = String(allow_none=True, metadata={"example": "ARV-2026-09"})
    next_due_date = Date(allow_none=True, metadata={"example": "2027-11-01"})
    given_by = String(allow_none=True, metadata={"example": "Dr. Meera Nair"})
    notes = String(allow_none=True)

    created_by = Integer(required=True)
    created_at = DateTime(required=True)
    updated_at = DateTime(required=True)


class VaccinationListOutSchema(Schema):
    """Paginated list response for vaccinations under a dog."""

    items = List(Nested(VaccinationOutSchema), required=True)
    page = Integer(required=True, metadata={"example": 1})
    per_page = Integer(required=True, metadata={"example": 20})
    total = Integer(required=True, metadata={"example": 1})


class VaccinationCreateInSchema(Schema):
    """Payload schema for recording a new vaccination."""

    vaccine_name = String(
        required=True,
        validate=Length(min=1, max=100),
        metadata={"example": "Anti-Rabies"},
    )
    date_given = Date(required=True, metadata={"example": "2026-11-01"})
    case_id = Integer(required=False, allow_none=True)
    batch_no = String(required=False, allow_none=True, validate=Length(max=50))
    next_due_date = Date(required=False, allow_none=True)
    given_by = String(required=False, allow_none=True, validate=Length(max=100))
    notes = String(required=False, allow_none=True)


class VaccinationUpdateInSchema(Schema):
    """Payload schema for updating an existing vaccination record."""

    vaccine_name = String(required=False, validate=Length(min=1, max=100))
    date_given = Date(required=False)
    case_id = Integer(required=False, allow_none=True)
    batch_no = String(required=False, allow_none=True, validate=Length(max=50))
    next_due_date = Date(required=False, allow_none=True)
    given_by = String(required=False, allow_none=True, validate=Length(max=100))
    notes = String(required=False, allow_none=True)


class VaccinationMessageOutSchema(Schema):
    """Standard message response for vaccination deletion."""

    message = String(required=True, metadata={"example": "Vaccination deleted successfully"})


class DueVaccinationQuerySchema(Schema):
    """Query parameter schema for due/overdue vaccinations."""

    days = Integer(
        load_default=30,
        validate=Range(min=1, max=365),
        metadata={"description": "Lookahead window in days (1-365)", "example": 30},
    )


class DueVaccinationItemSchema(Schema):
    """Summary item for an overdue or upcoming vaccination."""

    id = Integer(required=True)
    dog_id = Integer(required=True)
    dog_code = String(required=True, metadata={"example": "CTR-0001"})
    area_name = String(required=True, metadata={"example": "Central Zone - Ward 1"})
    area_color_hex = String(required=True, metadata={"example": "#0D9488"})
    case_id = Integer(allow_none=True)
    vaccine_name = String(required=True, metadata={"example": "Anti-Rabies"})
    date_given = Date(required=True)
    next_due_date = Date(required=True)
    days_until_due = Integer(
        required=True,
        metadata={"description": "Negative if overdue, 0+ if upcoming"},
    )
    given_by = String(allow_none=True)


class DueVaccinationsOutSchema(Schema):
    """Response schema grouping overdue and upcoming vaccinations."""

    days = Integer(required=True, metadata={"example": 30})
    as_of = Date(required=True)
    overdue = List(Nested(DueVaccinationItemSchema), required=True)
    upcoming = List(Nested(DueVaccinationItemSchema), required=True)
