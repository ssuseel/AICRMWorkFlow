"""Database-backed dashboard metrics."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import CRMSyncRecord, Email, EmailResponse, FollowUp, Lead


class DashboardService:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def _count(self, model: type, *filters) -> int:
        statement = select(func.count(model.id)).where(
            model.tenant_id == self.tenant_id, *filters
        )
        return int(self.session.scalar(statement) or 0)

    def metrics(self) -> dict[str, int]:
        return {
            "total_leads": self._count(Lead, Lead.deleted_at.is_(None)),
            "new_leads": self._count(
                Lead, Lead.status == "NEW", Lead.deleted_at.is_(None)
            ),
            "qualified_leads": self._count(
                Lead, Lead.status == "QUALIFIED", Lead.deleted_at.is_(None)
            ),
            "emails_generated": self._count(Email),
            "emails_awaiting_approval": self._count(
                Email, Email.status == "PENDING_APPROVAL"
            ),
            "emails_sent": self._count(Email, Email.status == "SENT"),
            "responses_received": self._count(EmailResponse),
            "followups_due": self._count(
                FollowUp, FollowUp.status.in_(["OPEN", "SCHEDULED", "OVERDUE"])
            ),
            "crm_sync_pending": self._count(
                CRMSyncRecord,
                CRMSyncRecord.status.in_(["PENDING", "IN_PROGRESS", "RETRY_SCHEDULED"]),
            ),
        }
