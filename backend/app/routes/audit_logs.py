"""Admin-only Audit Log inspection routes."""

from apiflask import APIBlueprint

from app.schemas.audit_log import AuditLogListOutSchema, AuditLogQuerySchema
from app.services import audit_service
from app.utils.auth import login_required, roles_required

audit_logs_bp = APIBlueprint(
    "audit_logs", __name__, url_prefix="/api/audit-logs", tag="Audit Logs"
)


@audit_logs_bp.get("", strict_slashes=False)
@audit_logs_bp.input(AuditLogQuerySchema, location="query")
@audit_logs_bp.output(AuditLogListOutSchema, status_code=200)
@audit_logs_bp.doc(
    summary="List audit logs (Admin only)",
    description="Retrieve paginated audit trail entries with optional filters.",
    security="BearerAuth",
)
@login_required
@roles_required("admin")
def list_audit_logs(query_data):
    """Retrieve filtered audit log entries."""
    return audit_service.list_audit_logs(query_data)
