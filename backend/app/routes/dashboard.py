"""Dashboard operational statistics routes."""

from apiflask import APIBlueprint

from app.schemas.dashboard import DashboardStatsOutSchema
from app.services import dashboard_service
from app.utils.auth import login_required

dashboard_bp = APIBlueprint(
    "dashboard", __name__, url_prefix="/api/dashboard", tag="Dashboard"
)


@dashboard_bp.get("/stats")
@dashboard_bp.output(DashboardStatsOutSchema, status_code=200)
@dashboard_bp.doc(
    summary="Get dashboard statistics",
    description="Return live totals, status breakdown, area counts, monthly sterilizations, and due vaccinations.",
    security="BearerAuth",
)
@login_required
def get_stats():
    """Return operational dashboard summary for authenticated staff."""
    return dashboard_service.get_dashboard_stats()
