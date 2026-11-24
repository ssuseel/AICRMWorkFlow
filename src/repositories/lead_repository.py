"""Tenant-aware lead repository."""

from datetime import UTC, datetime, time

from sqlalchemy import func, or_, select

from src.db.models import Lead
from src.repositories.base import TenantRepository


class LeadRepository(TenantRepository):
    def list_active(self) -> list[Lead]:
        statement = (
            select(Lead)
            .where(Lead.tenant_id == self.tenant_id, Lead.deleted_at.is_(None))
            .order_by(Lead.created_at.desc())
        )
        return list(self.session.scalars(statement).all())

    def find_by_email(self, email: str) -> Lead | None:
        statement = select(Lead).where(
            Lead.tenant_id == self.tenant_id,
            func.lower(Lead.email) == email.strip().lower(),
            Lead.deleted_at.is_(None),
        )
        return self.session.scalar(statement)

    def count_active(self) -> int:
        statement = select(func.count(Lead.id)).where(
            Lead.tenant_id == self.tenant_id,
            Lead.deleted_at.is_(None),
        )
        return int(self.session.scalar(statement) or 0)

    def get(self, lead_id: str) -> Lead | None:
        statement = select(Lead).where(
            Lead.tenant_id == self.tenant_id,
            Lead.id == lead_id,
            Lead.deleted_at.is_(None),
        )
        return self.session.scalar(statement)

    def search(
        self,
        *,
        query: str = "",
        source: str | None = None,
        industry: str | None = None,
        company: str | None = None,
        owner_id: str | None = None,
        status: str | None = None,
        min_score: int = 0,
        max_score: int = 100,
        created_from=None,
        created_to=None,
        next_follow_up_from=None,
        next_follow_up_to=None,
        sort: str = "created_at",
        direction: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Lead], int]:
        statement = select(Lead).where(
            Lead.tenant_id == self.tenant_id,
            Lead.deleted_at.is_(None),
        )
        if query:
            pattern = f"%{query.strip().lower()}%"
            statement = statement.where(
                or_(
                    func.lower(Lead.first_name).like(pattern),
                    func.lower(Lead.last_name).like(pattern),
                    func.lower(Lead.email).like(pattern),
                    func.lower(func.coalesce(Lead.company, "")).like(pattern),
                )
            )
        if source:
            statement = statement.where(Lead.source == source)
        if industry:
            statement = statement.where(Lead.industry == industry)
        if company:
            statement = statement.where(
                func.lower(Lead.company).like(f"%{company.lower()}%")
            )
        if owner_id:
            statement = statement.where(Lead.owner_id == owner_id)
        if status:
            statement = statement.where(Lead.status == status)
        statement = statement.where(
            Lead.qualification_score >= min_score,
            Lead.qualification_score <= max_score,
        )
        if created_from:
            statement = statement.where(
                Lead.created_at >= datetime.combine(created_from, time.min, UTC)
            )
        if created_to:
            statement = statement.where(
                Lead.created_at <= datetime.combine(created_to, time.max, UTC)
            )
        if next_follow_up_from:
            statement = statement.where(
                Lead.next_follow_up_at
                >= datetime.combine(next_follow_up_from, time.min, UTC)
            )
        if next_follow_up_to:
            statement = statement.where(
                Lead.next_follow_up_at
                <= datetime.combine(next_follow_up_to, time.max, UTC)
            )

        sort_columns = {
            "created_at": Lead.created_at,
            "company": Lead.company,
            "score": Lead.qualification_score,
            "status": Lead.status,
            "name": Lead.last_name,
            "next_follow_up": Lead.next_follow_up_at,
        }
        sort_column = sort_columns.get(sort, Lead.created_at)
        statement = statement.order_by(
            sort_column.desc() if direction == "desc" else sort_column.asc()
        )
        count_statement = select(func.count()).select_from(
            statement.order_by(None).subquery()
        )
        total = int(self.session.scalar(count_statement) or 0)
        offset = (page - 1) * page_size
        statement = statement.offset(offset).limit(page_size)
        return list(self.session.scalars(statement).all()), total
