"""Admin-only Excel and flat Analytics export routes."""

from apiflask import APIBlueprint
from flask import Response, current_app, jsonify, stream_with_context
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db, limiter
from app.schemas.export import AnalyticsExportQuerySchema
from app.services import analytics_service, export_service
from app.services.audit_service import log_audit
from app.utils.auth import get_current_user, login_required, roles_required
from app.utils.rate_limit import get_user_or_ip_key

exports_bp = APIBlueprint("exports", __name__, url_prefix="/api", tag="Exports & Analytics")


@exports_bp.get("/export/excel")
@limiter.limit(lambda: current_app.config["RATELIMIT_EXPORT"], key_func=get_user_or_ip_key)
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
    actor = get_current_user()
    xlsx_bytes, row_count = export_service.build_excel_export()
    try:
        log_audit(
            action="export",
            table_name="export_excel",
            record_id=0,
            user_id=actor.id,
            changes={"format": "xlsx", "dataset": "all", "row_count": row_count},
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return Response(
        xlsx_bytes,
        status=200,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="dog_sterilization_export.xlsx"'
        },
    )


@exports_bp.get("/analytics/export")
@limiter.limit(lambda: current_app.config["RATELIMIT_EXPORT"], key_func=get_user_or_ip_key)
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
    actor = get_current_user()
    fmt = query_data.get("format", "csv")
    include_personal = bool(query_data.get("include_personal", False))
    columns, rows = analytics_service.build_analytics_rows(
        include_personal=include_personal
    )

    try:
        log_audit(
            action="export",
            table_name="analytics_export",
            record_id=0,
            user_id=actor.id,
            changes={
                "format": fmt,
                "dataset": "analytics",
                "include_personal": include_personal,
                "row_count": len(rows),
            },
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

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
