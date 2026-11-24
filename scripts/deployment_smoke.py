"""Verify migrated demo database tables and dashboard queries."""

from sqlalchemy import inspect

from src.config.settings import get_settings
from src.db.session import SessionLocal, engine
from src.services.dashboard_service import DashboardService

REQUIRED_TABLES = {
    "tenants",
    "users",
    "leads",
    "emails",
    "email_responses",
    "follow_ups",
    "crm_sync_records",
    "crm_connections",
    "crm_mappings",
    "audit_events",
}


def main() -> None:
    existing_tables = set(inspect(engine).get_table_names())
    missing = REQUIRED_TABLES - existing_tables
    if missing:
        raise RuntimeError(f"Deployment database is missing tables: {sorted(missing)}")

    tenant_id = str(get_settings().default_tenant_id)
    with SessionLocal() as session:
        metrics = DashboardService(session, tenant_id).metrics()
    if metrics["total_leads"] < 1:
        raise RuntimeError("Deployment smoke test expected seeded demonstration leads")
    print(
        "Deployment smoke check passed: "
        f"{metrics['total_leads']} demo leads and {len(existing_tables)} tables."
    )


if __name__ == "__main__":
    main()
