"""Schemas for Dashboard statistics endpoint."""

from apiflask import Schema
from apiflask.fields import Dict, Integer, List, Nested, String


class AreaDogCountSchema(Schema):
    """Dog count summary grouped by operational area."""

    area_id = Integer(required=True, metadata={"example": 1})
    area_name = String(required=True, metadata={"example": "Central Zone - Ward 1"})
    short_code = String(required=True, metadata={"example": "CTR"})
    color_hex = String(required=True, metadata={"example": "#0D9488"})
    count = Integer(required=True, metadata={"example": 12})


class VaccinationDueCountsSchema(Schema):
    """Counts of overdue and upcoming vaccinations."""

    overdue = Integer(required=True, metadata={"example": 3})
    upcoming_30_days = Integer(required=True, metadata={"example": 5})


class DashboardStatsOutSchema(Schema):
    """Aggregated operational dashboard statistics."""

    total_dogs = Integer(required=True, metadata={"example": 45})
    by_status = Dict(keys=String(), values=Integer(), required=True)
    by_area = List(Nested(AreaDogCountSchema), required=True)
    sterilized_this_month = Integer(required=True, metadata={"example": 14})
    vaccinations_due = Nested(VaccinationDueCountsSchema, required=True)
