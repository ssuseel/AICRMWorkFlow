"""Tenant-scoped database analytics."""

from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session

from src.db.models import (
    CRMSyncRecord,
    Email,
    EmailResponse,
    FollowUp,
    Lead,
    User,
)
from src.domain.analytics import AnalyticsFilters


class AnalyticsService:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def _lead_conditions(
        self,
        filters: AnalyticsFilters,
        *,
        include_date: bool = True,
    ) -> list[Any]:
        conditions: list[Any] = [
            Lead.tenant_id == self.tenant_id,
            Lead.deleted_at.is_(None),
        ]
        if include_date and filters.start_date:
            conditions.append(
                Lead.created_at
                >= datetime.combine(filters.start_date, time.min, tzinfo=UTC)
            )
        if include_date and filters.end_date:
            conditions.append(
                Lead.created_at
                <= datetime.combine(filters.end_date, time.max, tzinfo=UTC)
            )
        if filters.owner_id:
            conditions.append(Lead.owner_id == filters.owner_id)
        if filters.industry:
            conditions.append(Lead.industry == filters.industry)
        if filters.source:
            conditions.append(Lead.source == filters.source)
        if filters.status:
            conditions.append(Lead.status == filters.status)
        return conditions

    def _period_conditions(self, column, filters: AnalyticsFilters) -> list[Any]:
        conditions: list[Any] = []
        if filters.start_date:
            conditions.append(
                column >= datetime.combine(filters.start_date, time.min, tzinfo=UTC)
            )
        if filters.end_date:
            conditions.append(
                column <= datetime.combine(filters.end_date, time.max, tzinfo=UTC)
            )
        return conditions

    def acquisition_trends(
        self,
        filters: AnalyticsFilters,
    ) -> list[dict[str, Any]]:
        statement = (
            select(
                func.date(Lead.created_at).label("date"),
                func.count(Lead.id).label("leads"),
            )
            .where(*self._lead_conditions(filters))
            .group_by(func.date(Lead.created_at))
            .order_by(func.date(Lead.created_at))
        )
        return [
            {"date": str(row.date), "leads": int(row.leads)}
            for row in self.session.execute(statement)
        ]

    def qualification_distribution(
        self,
        filters: AnalyticsFilters,
    ) -> list[dict[str, Any]]:
        bucket = case(
            (Lead.qualification_score < 40, "0-39"),
            (Lead.qualification_score < 70, "40-69"),
            else_="70-100",
        ).label("score_band")
        statement = (
            select(bucket, func.count(Lead.id).label("leads"))
            .where(*self._lead_conditions(filters))
            .group_by(bucket)
            .order_by(bucket)
        )
        return [
            {"score_band": row.score_band, "leads": int(row.leads)}
            for row in self.session.execute(statement)
        ]

    def conversion_metrics(self, filters: AnalyticsFilters) -> dict[str, Any]:
        customer_count = func.sum(case((Lead.status == "CUSTOMER", 1), else_=0))
        statement = select(
            func.count(Lead.id).label("leads"),
            customer_count.label("customers"),
        ).where(*self._lead_conditions(filters))
        row = self.session.execute(statement).one()
        leads = int(row.leads or 0)
        customers = int(row.customers or 0)
        return {
            "leads": leads,
            "customers": customers,
            "conversion_rate": customers / leads if leads else 0.0,
        }

    def email_metrics(self, filters: AnalyticsFilters) -> dict[str, Any]:
        conditions = [
            Email.tenant_id == self.tenant_id,
            *self._lead_conditions(filters, include_date=False),
            *self._period_conditions(Email.created_at, filters),
        ]

        statement = (
            select(
                func.sum(case((Email.status == "SENT", 1), else_=0)).label("sent"),
                func.sum(
                    case(
                        (
                            Email.status.in_(["SENT", "BOUNCED", "DELIVERY_FAILED"]),
                            1,
                        ),
                        else_=0,
                    )
                ).label("attempted"),
                func.count(distinct(EmailResponse.id)).label("responses"),
            )
            .select_from(Email)
            .join(Lead, Email.lead_id == Lead.id)
            .outerjoin(
                EmailResponse,
                (EmailResponse.email_id == Email.id)
                & (EmailResponse.tenant_id == self.tenant_id),
            )
            .where(*conditions)
        )
        row = self.session.execute(statement).one()
        sent = int(row.sent or 0)
        attempted = int(row.attempted or 0)
        responses = int(row.responses or 0)
        return {
            "sent": sent,
            "attempted": attempted,
            "responses": responses,
            "delivery_rate": sent / attempted if attempted else 0.0,
            "response_rate": responses / sent if sent else 0.0,
        }

    def follow_up_effectiveness(
        self,
        filters: AnalyticsFilters,
    ) -> dict[str, Any]:
        conditions = [
            FollowUp.tenant_id == self.tenant_id,
            *self._lead_conditions(filters, include_date=False),
            *self._period_conditions(FollowUp.created_at, filters),
        ]
        statement = (
            select(
                func.count(FollowUp.id).label("total"),
                func.sum(case((FollowUp.status == "COMPLETED", 1), else_=0)).label(
                    "completed"
                ),
                func.sum(case((FollowUp.status == "OVERDUE", 1), else_=0)).label(
                    "overdue"
                ),
                func.count(
                    distinct(
                        case(
                            (
                                (FollowUp.status == "COMPLETED")
                                & (Lead.status == "CUSTOMER"),
                                Lead.id,
                            )
                        )
                    )
                ).label("converted_leads"),
            )
            .select_from(FollowUp)
            .join(Lead, FollowUp.lead_id == Lead.id)
            .where(*conditions)
        )
        row = self.session.execute(statement).one()
        total = int(row.total or 0)
        completed = int(row.completed or 0)
        return {
            "total": total,
            "completed": completed,
            "overdue": int(row.overdue or 0),
            "converted_leads": int(row.converted_leads or 0),
            "completion_rate": completed / total if total else 0.0,
        }

    def pipeline_activity(
        self,
        filters: AnalyticsFilters,
    ) -> list[dict[str, Any]]:
        statement = (
            select(Lead.status, func.count(Lead.id).label("leads"))
            .where(*self._lead_conditions(filters))
            .group_by(Lead.status)
            .order_by(Lead.status)
        )
        return [
            {"status": row.status, "leads": int(row.leads)}
            for row in self.session.execute(statement)
        ]

    def crm_health(self, filters: AnalyticsFilters) -> list[dict[str, Any]]:
        conditions = [
            CRMSyncRecord.tenant_id == self.tenant_id,
            *self._period_conditions(CRMSyncRecord.created_at, filters),
            *self._lead_conditions(filters, include_date=False),
        ]
        statement = (
            select(
                CRMSyncRecord.status,
                func.count(CRMSyncRecord.id).label("records"),
            )
            .select_from(CRMSyncRecord)
            .join(Lead, CRMSyncRecord.lead_id == Lead.id)
            .where(*conditions)
            .group_by(CRMSyncRecord.status)
            .order_by(CRMSyncRecord.status)
        )
        return [
            {"status": row.status, "records": int(row.records)}
            for row in self.session.execute(statement)
        ]

    def team_productivity(
        self,
        filters: AnalyticsFilters,
    ) -> list[dict[str, Any]]:
        qualified = func.sum(
            case((Lead.status.in_(["QUALIFIED", "CUSTOMER"]), 1), else_=0)
        )
        customers = func.sum(case((Lead.status == "CUSTOMER", 1), else_=0))
        statement = (
            select(
                User.id.label("owner_id"),
                User.display_name.label("owner"),
                func.count(Lead.id).label("leads"),
                qualified.label("qualified"),
                customers.label("customers"),
            )
            .select_from(Lead)
            .outerjoin(
                User,
                (Lead.owner_id == User.id) & (User.tenant_id == self.tenant_id),
            )
            .where(*self._lead_conditions(filters))
            .group_by(User.id, User.display_name)
            .order_by(User.display_name)
        )
        productivity = {
            row.owner_id: {
                "owner": row.owner or "Unassigned",
                "leads": int(row.leads),
                "qualified": int(row.qualified or 0),
                "customers": int(row.customers or 0),
                "emails_sent": 0,
            }
            for row in self.session.execute(statement)
        }
        email_statement = (
            select(
                Lead.owner_id,
                func.count(Email.id).label("emails_sent"),
            )
            .select_from(Email)
            .join(Lead, Email.lead_id == Lead.id)
            .where(
                Email.tenant_id == self.tenant_id,
                Email.status == "SENT",
                *self._lead_conditions(filters, include_date=False),
                *self._period_conditions(Email.created_at, filters),
            )
            .group_by(Lead.owner_id)
        )
        for row in self.session.execute(email_statement):
            if row.owner_id in productivity:
                productivity[row.owner_id]["emails_sent"] = int(row.emails_sent)
        return list(productivity.values())

    def summary(self, filters: AnalyticsFilters) -> dict[str, Any]:
        return {
            "acquisition_trends": self.acquisition_trends(filters),
            "qualification_distribution": self.qualification_distribution(filters),
            "conversion": self.conversion_metrics(filters),
            "email": self.email_metrics(filters),
            "follow_ups": self.follow_up_effectiveness(filters),
            "pipeline": self.pipeline_activity(filters),
            "crm_health": self.crm_health(filters),
            "team_productivity": self.team_productivity(filters),
        }
