"""Base tenant-aware repository helpers."""

from sqlalchemy.orm import Session


class TenantRepository:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
