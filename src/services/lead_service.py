"""Lead capture and duplicate handling service."""

import csv
import io
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.db.models import Email, FollowUp, Lead
from src.domain.enums import LeadStatus
from src.domain.schemas import LeadCreate, LeadUpdate
from src.repositories.lead_repository import LeadRepository


class DuplicateLeadError(ValueError):
    pass


class LeadDeleteRestrictedError(ValueError):
    pass


class LeadService:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.repository = LeadRepository(session, tenant_id)
        self.tenant_id = tenant_id

    def create(self, data: LeadCreate) -> Lead:
        email = str(data.email).strip().lower()
        if self.repository.find_by_email(email):
            raise DuplicateLeadError("A lead with this email already exists")

        lead = Lead(
            tenant_id=self.tenant_id,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            email=email,
            phone=data.phone,
            company=data.company,
            title=data.title,
            industry=data.industry,
            source=data.source,
            status="NEW",
            owner_id=str(data.owner_id) if data.owner_id else None,
        )
        self.session.add(lead)
        self.session.commit()
        self.session.refresh(lead)
        return lead

    def update(self, lead_id: str, data: LeadUpdate) -> Lead:
        lead = self.repository.get(lead_id)
        if lead is None:
            raise LookupError("Lead not found")
        if data.email is not None:
            email = str(data.email).strip().lower()
            duplicate = self.repository.find_by_email(email)
            if duplicate is not None and duplicate.id != lead_id:
                raise DuplicateLeadError("A lead with this email already exists")
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            if field == "email" and value is not None:
                value = str(value).strip().lower()
            elif field == "owner_id" and value is not None:
                value = str(value)
            elif field == "status" and value is not None:
                LeadStatus(value)
            setattr(lead, field, value)
        self.session.commit()
        self.session.refresh(lead)
        return lead

    def assign_owner(self, lead_id: str, owner_id: str | None) -> Lead:
        return self.update(lead_id, LeadUpdate(owner_id=owner_id))

    def change_status(self, lead_id: str, status: LeadStatus) -> Lead:
        lead = self.repository.get(lead_id)
        if lead is None:
            raise LookupError("Lead not found")
        lead.status = status.value
        self.session.commit()
        self.session.refresh(lead)
        return lead

    def soft_delete(self, lead_id: str) -> Lead:
        lead = self.repository.get(lead_id)
        if lead is None:
            raise LookupError("Lead not found")
        protected_email = (
            self.session.query(Email)
            .filter(
                Email.tenant_id == self.tenant_id,
                Email.lead_id == lead_id,
                Email.status.in_(["APPROVED", "PENDING_APPROVAL", "SENT", "SENDING"]),
            )
            .first()
        )
        if protected_email:
            raise LeadDeleteRestrictedError(
                "Lead cannot be deleted while an email is approved, pending approval, or sent"
            )
        active_follow_up = (
            self.session.query(FollowUp)
            .filter(
                FollowUp.tenant_id == self.tenant_id,
                FollowUp.lead_id == lead_id,
                FollowUp.status.in_(["OPEN", "SCHEDULED", "OVERDUE"]),
            )
            .first()
        )
        if active_follow_up:
            raise LeadDeleteRestrictedError(
                "Lead cannot be deleted while an active follow-up exists"
            )
        lead.deleted_at = datetime.now(UTC)
        lead.status = LeadStatus.DELETED.value
        self.session.commit()
        self.session.refresh(lead)
        return lead

    def import_csv(self, content: str) -> dict[str, int]:
        reader = csv.DictReader(io.StringIO(content))
        counts = {"created": 0, "duplicates": 0, "rejected": 0, "rows": 0}
        required = {"first_name", "last_name", "email"}
        if not reader.fieldnames or not required.issubset(
            {name.strip().lower() for name in reader.fieldnames}
        ):
            counts["rejected"] = 1
            counts["rows"] = 1
            return counts

        normalized_fieldnames = {
            name.strip().lower(): name for name in reader.fieldnames
        }
        for row in reader:
            counts["rows"] += 1
            values = {
                key: row.get(normalized_fieldnames.get(key, key), "")
                for key in required
            }
            try:
                data = LeadCreate(
                    first_name=str(values["first_name"] or "").strip(),
                    last_name=str(values["last_name"] or "").strip(),
                    email=str(values["email"] or "").strip(),
                    phone=str(
                        row.get(normalized_fieldnames.get("phone", "phone"), "") or ""
                    ).strip()
                    or None,
                    company=str(
                        row.get(normalized_fieldnames.get("company", "company"), "")
                        or ""
                    ).strip()
                    or None,
                    title=str(
                        row.get(normalized_fieldnames.get("title", "title"), "") or ""
                    ).strip()
                    or None,
                    industry=str(
                        row.get(normalized_fieldnames.get("industry", "industry"), "")
                        or ""
                    ).strip()
                    or None,
                    source=str(
                        row.get(normalized_fieldnames.get("source", "source"), "")
                        or "CSV"
                    ).strip()
                    or "CSV",
                )
                self.create(data)
                counts["created"] += 1
            except DuplicateLeadError:
                counts["duplicates"] += 1
            except ValidationError:
                counts["rejected"] += 1
        return counts
