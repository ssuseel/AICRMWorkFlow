"""Seed a safe, realistic demonstration workspace."""
# ruff: noqa: E501

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import sessionmaker

from src.config.settings import get_settings
from src.db.base import Base
from src.db.models import (
    CRMConnection,
    CRMFieldMapping,
    CRMSyncRecord,
    Email,
    EmailResponse,
    FollowUp,
    Lead,
    LeadQualification,
    Tenant,
    User,
)
from src.db.session import create_database_engine, engine


def seed(database_url: str | None = None) -> dict[str, int]:
    target_engine = (
        engine if database_url is None else create_database_engine(database_url)
    )
    Base.metadata.create_all(target_engine)
    settings = get_settings()
    tenant_id = str(settings.default_tenant_id)
    now = datetime.now(UTC)

    session_factory = sessionmaker(bind=target_engine)
    with session_factory() as session:
        tenant = session.get(Tenant, tenant_id)
        if tenant is None:
            tenant = Tenant(
                id=tenant_id,
                name="Northstar Revenue Operations",
                slug="northstar-revenue",
                status="active",
            )
            session.add(tenant)

        owner_specs = [
            ("Jordan Lee", "jordan.lee@northstar.example"),
            ("Morgan Chen", "morgan.chen@northstar.example"),
            ("Taylor Rivera", "taylor.rivera@northstar.example"),
        ]
        owners = {}
        for name, email in owner_specs:
            user = (
                session.query(User).filter_by(tenant_id=tenant_id, email=email).first()
            )
            if user is None:
                user = User(
                    tenant_id=tenant_id,
                    email=email,
                    display_name=name,
                    role="sales",
                )
                session.add(user)
                session.flush()
            owners[name] = user.id

        lead_rows = [
            (
                "Asha",
                "Patel",
                "asha.patel@northwind.example",
                "Northwind Manufacturing",
                "Manufacturing",
                "Website",
                "QUALIFIED",
                82,
                "VP of Operations",
                "+1-206-555-0141",
            ),
            (
                "Mateo",
                "Garcia",
                "mateo.garcia@contoso.example",
                "Contoso Logistics",
                "Logistics",
                "Referral",
                "NEW",
                0,
                "Fleet Director",
                "+1-512-555-0188",
            ),
            (
                "Priya",
                "Singh",
                "priya.singh@fabrikam.example",
                "Fabrikam Health",
                "Healthcare",
                "Conference",
                "CONTACTED",
                65,
                "Director of Digital Health",
                "+1-617-555-0127",
            ),
            (
                "Noah",
                "Williams",
                "noah.williams@tailspin.example",
                "Tailspin Software",
                "Technology",
                "CSV",
                "VALIDATED",
                45,
                "Head of Customer Success",
                "+1-303-555-0164",
            ),
            (
                "Eva",
                "Brown",
                "eva.brown@adatum.example",
                "Adatum Retail",
                "Retail",
                "Campaign",
                "NEW",
                20,
                "E-commerce Manager",
                "+1-415-555-0192",
            ),
            (
                "Liam",
                "Davis",
                "liam.davis@blueyonder.example",
                "Blue Yonder Energy",
                "Energy",
                "Webinar",
                "CUSTOMER",
                91,
                "Chief Technology Officer",
                "+1-713-555-0136",
            ),
            (
                "Sophia",
                "Wilson",
                "sophia.wilson@coho.example",
                "Coho Aviation",
                "Aviation",
                "Partner",
                "ENGAGED",
                76,
                "VP of Commercial Operations",
                "+1-425-555-0173",
            ),
            (
                "Oliver",
                "Martinez",
                "oliver.martinez@litware.example",
                "Litware Finance",
                "Financial Services",
                "Email",
                "SUPPRESSED",
                28,
                "Finance Systems Analyst",
                "+1-212-555-0119",
            ),
            (
                "Mia",
                "Anderson",
                "mia.anderson@proseware.example",
                "Proseware Media",
                "Media",
                "Website",
                "VALIDATED",
                58,
                "Marketing Operations Lead",
                "+1-503-555-0158",
            ),
            (
                "James",
                "Thomas",
                "james.thomas@wingtip.example",
                "Wingtip Toys",
                "Retail",
                "Campaign",
                "NEW",
                12,
                "Procurement Coordinator",
                "+1-972-555-0161",
            ),
            (
                "Isabella",
                "Moore",
                "isabella.moore@citypower.example",
                "City Power Utilities",
                "Utilities",
                "Referral",
                "CONTACTED",
                68,
                "Grid Operations Manager",
                "+1-602-555-0198",
            ),
            (
                "Benjamin",
                "Taylor",
                "benjamin.taylor@wideworld.example",
                "Wide World Importers",
                "Wholesale",
                "Conference",
                "QUALIFIED",
                88,
                "Chief Revenue Officer",
                "+1-312-555-0105",
            ),
        ]
        created_leads = 0
        owner_names = list(owners)
        followup_offsets = [-2, 1, 2, 4, 1, 7, 3, -5, 5, 6, 2, 1]
        age_offsets = [45, 38, 31, 27, 24, 62, 36, 52, 29, 20, 19, 41]

        for index, (
            first,
            last,
            email,
            company,
            industry,
            source,
            status,
            score,
            title,
            phone,
        ) in enumerate(lead_rows):
            lead = session.query(Lead).filter_by(
                tenant_id=tenant_id, email=email
            ).first()
            if lead is None:
                lead = Lead(
                    tenant_id=tenant_id,
                    first_name=first,
                    last_name=last,
                    email=email,
                    phone=phone,
                    company=company,
                    title=title,
                    industry=industry,
                    source=source,
                    status=status,
                    qualification_score=score,
                    qualification_status=(
                        "qualified"
                        if status in {"QUALIFIED", "ENGAGED", "CUSTOMER"}
                        else "pending"
                        if status in {"NEW", "VALIDATED"}
                        else None
                    ),
                    next_follow_up_at=now + timedelta(days=followup_offsets[index]),
                    created_at=now - timedelta(days=age_offsets[index]),
                    owner_id=owners[owner_names[index % 3]],
                )
                session.add(lead)
                created_leads += 1
            else:
                lead.phone = phone
                lead.title = title
                lead.industry = industry
                lead.status = status
                lead.qualification_score = score
                lead.next_follow_up_at = now + timedelta(
                    days=followup_offsets[index]
                )
                lead.owner_id = lead.owner_id or owners[owner_names[index % 3]]

        session.flush()
        leads_by_email = {
            lead.email: lead
            for lead in session.query(Lead).filter_by(tenant_id=tenant_id).all()
        }

        session.commit()
        return {
            "tenant_id": tenant_id,
            "created_or_existing_leads": len(lead_rows),
            "created_leads": created_leads,
        }


if __name__ == "__main__":
    print(seed())
