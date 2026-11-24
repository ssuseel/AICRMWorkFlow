"""Persistent follow-up scheduling and business-day calculations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.db.models import FollowUp, Lead
from src.domain.enums import FollowUpStatus
from src.domain.schemas import FollowUpCreate


class FollowUpService:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    @staticmethod
    def add_business_days(start: datetime, days: int) -> datetime:
        result = start
        remaining = max(0, days)
        while remaining:
            result += timedelta(days=1)
            if result.weekday() < 5:
                remaining -= 1
        return result

    def create(self, data: FollowUpCreate) -> FollowUp:
        lead = (
            self.session.query(Lead)
            .filter(
                Lead.tenant_id == self.tenant_id,
                Lead.id == str(data.lead_id),
                Lead.deleted_at.is_(None),
            )
            .first()
        )
        if lead is None:
            raise LookupError("Lead not found")
        follow_up = FollowUp(
            tenant_id=self.tenant_id,
            lead_id=lead.id,
            owner_id=str(data.owner_id) if data.owner_id else lead.owner_id,
            title=data.title.strip(),
            description=data.description,
            priority=data.priority,
            status=FollowUpStatus.OPEN.value,
            due_at=data.due_at,
        )
        self.session.add(follow_up)
        self.session.commit()
        self.session.refresh(follow_up)
        return follow_up

    def schedule_business_follow_up(
        self,
        lead_id: str,
        title: str,
        days: int = 3,
        priority: str = "medium",
    ) -> FollowUp:
        lead = (
            self.session.query(Lead)
            .filter(
                Lead.tenant_id == self.tenant_id,
                Lead.id == lead_id,
                Lead.deleted_at.is_(None),
            )
            .first()
        )
        if lead is None:
            raise LookupError("Lead not found")
        due_at = self.add_business_days(datetime.now(UTC), days)
        follow_up = FollowUp(
            tenant_id=self.tenant_id,
            lead_id=lead.id,
            owner_id=lead.owner_id,
            title=title,
            priority=priority,
            status=FollowUpStatus.SCHEDULED.value,
            scheduled_at=datetime.now(UTC),
            due_at=due_at,
        )
        self.session.add(follow_up)
        lead.next_follow_up_at = due_at
        self.session.commit()
        self.session.refresh(follow_up)
        return follow_up

    def reschedule(self, follow_up_id: str, due_at: datetime) -> FollowUp:
        follow_up = self._get(follow_up_id)
        if follow_up.status == FollowUpStatus.CANCELLED.value:
            raise ValueError("Cancelled follow-ups cannot be rescheduled")
        follow_up.due_at = due_at
        follow_up.status = FollowUpStatus.SCHEDULED.value
        follow_up.scheduled_at = datetime.now(UTC)
        lead = self.session.get(Lead, follow_up.lead_id)
        if lead:
            lead.next_follow_up_at = due_at
        self.session.commit()
        self.session.refresh(follow_up)
        return follow_up

    def complete(self, follow_up_id: str) -> FollowUp:
        follow_up = self._get(follow_up_id)
        follow_up.status = FollowUpStatus.COMPLETED.value
        follow_up.completed_at = datetime.now(UTC)
        lead = self.session.get(Lead, follow_up.lead_id)
        if lead:
            lead.next_follow_up_at = None
        self.session.commit()
        self.session.refresh(follow_up)
        return follow_up

    def cancel(self, follow_up_id: str, reason: str) -> FollowUp:
        follow_up = self._get(follow_up_id)
        follow_up.status = FollowUpStatus.CANCELLED.value
        follow_up.cancelled_at = datetime.now(UTC)
        follow_up.cancellation_reason = reason
        self.session.commit()
        self.session.refresh(follow_up)
        return follow_up

    def mark_overdue(self) -> int:
        now = datetime.now(UTC)
        follow_ups = (
            self.session.query(FollowUp)
            .filter(
                FollowUp.tenant_id == self.tenant_id,
                FollowUp.status == FollowUpStatus.SCHEDULED.value,
                FollowUp.due_at < now,
            )
            .all()
        )
        for follow_up in follow_ups:
            follow_up.status = FollowUpStatus.OVERDUE.value
        self.session.commit()
        return len(follow_ups)

    def list_due(self) -> list[FollowUp]:
        now = datetime.now(UTC)
        return list(
            self.session.query(FollowUp)
            .filter(
                FollowUp.tenant_id == self.tenant_id,
                FollowUp.status.in_(["OPEN", "SCHEDULED", "OVERDUE"]),
                FollowUp.due_at <= now,
            )
            .order_by(FollowUp.priority.desc(), FollowUp.due_at.asc())
            .all()
        )

    def list_all(self) -> list[FollowUp]:
        return list(
            self.session.query(FollowUp)
            .filter(FollowUp.tenant_id == self.tenant_id)
            .order_by(FollowUp.due_at.asc())
            .all()
        )

    def _get(self, follow_up_id: str) -> FollowUp:
        follow_up = (
            self.session.query(FollowUp)
            .filter(
                FollowUp.tenant_id == self.tenant_id,
                FollowUp.id == follow_up_id,
            )
            .first()
        )
        if follow_up is None:
            raise LookupError("Follow-up not found")
        return follow_up
