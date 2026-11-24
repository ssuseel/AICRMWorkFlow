"""Dashboard metric tests."""

from src.db.models import Tenant
from src.services.dashboard_service import DashboardService


def test_empty_dashboard_metrics(session):
    tenant = Tenant(name="Empty", slug="empty")
    session.add(tenant)
    session.commit()

    metrics = DashboardService(session, tenant.id).metrics()
    assert metrics["total_leads"] == 0
    assert metrics["emails_sent"] == 0
