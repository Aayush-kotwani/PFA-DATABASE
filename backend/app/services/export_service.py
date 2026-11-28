"""Excel (.xlsx) export service for Admin reporting."""

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.orm import joinedload

from app.models.case import Case
from app.models.dog import Dog
from app.models.vaccination import Vaccination
from app.utils.export_sanitize import sanitize_export_cell


def _excel_val(val: Any) -> Any:
    """Normalize dates, datetimes, and Decimals, and neutralize formula injection."""
    if isinstance(val, datetime):
        return val.isoformat(sep=" ", timespec="seconds")
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    return sanitize_export_cell(val)


def _populate_sheet(ws, headers: list[str], rows: list[list[Any]]) -> None:
    """Write bold headers, data rows, and auto-adjusted column widths to a worksheet."""
    ws.append(headers)
    bold_font = Font(bold=True)
    for cell in ws[1]:
        cell.font = bold_font

    for row in rows:
        ws.append([_excel_val(v) for v in row])

    for col_cells in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col_cells), default=10)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 45)


def build_excel_export() -> bytes:
    """Generate a 3-sheet Excel workbook (Dogs, Cases, Vaccinations) in memory."""
    wb = Workbook()

    # Sheet 1: Dogs (includes guardian_phone for admin export)
    dogs_ws = wb.active
    dogs_ws.title = "Dogs"
    dogs = (
        Dog.query.options(joinedload(Dog.area))
        .filter(Dog.is_deleted.is_(False))
        .order_by(Dog.id.asc())
        .all()
    )
    dog_headers = [
        "ID", "Dog Code", "Area Name", "Area Code", "Sex", "Approx Age",
        "Age Group", "Coat Description", "Weight (kg)", "Body Condition",
        "Is Pregnant", "Temperament", "Guardian Name", "Guardian Phone",
        "Capture Address", "Landmark", "Latitude", "Longitude", "Maps URL",
        "Ear Notch Done", "Status", "Medical Conditions", "Medical History",
        "Created At",
    ]
    dog_rows = [
        [
            d.id, d.dog_code, d.area.name, d.area.short_code, d.sex,
            d.approx_age, d.age_group, d.coat_description, d.weight_kg,
            d.body_condition, d.is_pregnant, d.temperament, d.guardian_name,
            d.guardian_phone, d.capture_address, d.landmark, d.latitude,
            d.longitude, d.maps_url, d.ear_notch_done, d.status,
            d.medical_conditions, d.medical_history, d.created_at,
        ]
        for d in dogs
    ]
    _populate_sheet(dogs_ws, dog_headers, dog_rows)

    # Sheet 2: Cases
    cases_ws = wb.create_sheet(title="Cases")
    cases = (
        Case.query.join(Dog, Case.dog_id == Dog.id)
        .options(joinedload(Case.dog))
        .filter(Case.is_deleted.is_(False), Dog.is_deleted.is_(False))
        .order_by(Case.id.asc())
        .all()
    )
    case_headers = [
        "ID", "Dog Code", "Pickup Date", "Pickup Location", "Picked By",
        "Surgery Date", "Procedure", "Surgeon Name", "Surgery Outcome",
        "Complication Type", "Recovery Days", "Pre-Op Notes", "Post-Op Notes",
        "Prescription Details", "Complications", "Drop Date", "Drop Location",
        "Released Same Spot", "Created At",
    ]
    case_rows = [
        [
            c.id, c.dog.dog_code, c.pickup_date, c.pickup_location, c.picked_by,
            c.surgery_date, c.procedure, c.surgeon_name, c.surgery_outcome,
            c.complication_type, c.recovery_days, c.pre_op_notes, c.post_op_notes,
            c.prescription_details, c.complications, c.drop_date, c.drop_location,
            c.released_same_spot, c.created_at,
        ]
        for c in cases
    ]
    _populate_sheet(cases_ws, case_headers, case_rows)

    # Sheet 3: Vaccinations
    vax_ws = wb.create_sheet(title="Vaccinations")
    vaccinations = (
        Vaccination.query.join(Dog, Vaccination.dog_id == Dog.id)
        .options(joinedload(Vaccination.dog))
        .filter(Vaccination.is_deleted.is_(False), Dog.is_deleted.is_(False))
        .order_by(Vaccination.id.asc())
        .all()
    )
    vax_headers = [
        "ID", "Dog Code", "Case ID", "Vaccine Name", "Date Given",
        "Batch No", "Next Due Date", "Given By", "Notes", "Created At",
    ]
    vax_rows = [
        [
            v.id, v.dog.dog_code, v.case_id, v.vaccine_name, v.date_given,
            v.batch_no, v.next_due_date, v.given_by, v.notes, v.created_at,
        ]
        for v in vaccinations
    ]
    _populate_sheet(vax_ws, vax_headers, vax_rows)

    buf = BytesIO()
    wb.save(buf)
    total_rows = len(dogs) + len(cases) + len(vaccinations)
    return buf.getvalue(), total_rows
