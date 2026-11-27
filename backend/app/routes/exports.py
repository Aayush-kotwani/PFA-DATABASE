"""Admin-only Excel and flat Analytics export routes."""

from apiflask import APIBlueprint
from flask import Response, jsonify, stream_with_context

from app.schemas.export import AnalyticsExportQuerySchema
from app.services import analytics_service, export_service
from app.utils.auth import login_required, roles_required

exports_bp = APIBlueprint("exports", __name__, url_prefix="/api", tag="Exports & Analytics")


@exports_bp.get("/export/excel")
@exports_bp.doc(
    summary="Export workbook to Excel (Admin only)",
    description="Download a 3-sheet .xlsx workbook (Dogs, Cases, Vaccinations).",
    security="BearerAuth",
    responses={
        200: {
            "description": "Excel (.xlsx) file download",
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
        }
    },
)
@login_required
@roles_required("admin")
def export_excel():
    """Generate and download the multi-sheet Excel workbook."""
    xlsx_bytes = export_service.build_excel_export()
    return Response(
        xlsx_bytes,
        status=200,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="dog_sterilization_export.xlsx"'
        },
    )


@exports_bp.get("/analytics/export")
@exports_bp.input(AnalyticsExportQuerySchema, location="query")
@exports_bp.doc(
    summary="Export flat analytics dataset (Admin only)",
    description="Export flat joined dog+area+latest_case+vaccination_count as CSV (streamed) or JSON. Personal data is excluded by default.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def export_analytics(query_data):
    """Return unpaginated flat analytics data in CSV or JSON format."""
    fmt = query_data.get("format", "csv")
    include_personal = bool(query_data.get("include_personal", False))
    columns, rows = analytics_service.build_analytics_rows(
        include_personal=include_personal
    )

    if fmt == "json":
        return jsonify(
            {
                "count": len(rows),
                "include_personal": include_personal,
                "items": rows,
            }
        )

    return Response(
        stream_with_context(analytics_service.stream_analytics_csv(columns, rows)),
        status=200,
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="dogs_analytics.csv"'},
    )
