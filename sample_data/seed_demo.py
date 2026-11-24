"""Seed a safe demonstration workspace."""

from src.config.settings import get_settings
from src.db.base import Base
from src.db.models import FollowUp, Lead, Tenant, User
from src.db.session import create_database_engine, engine


def seed(database_url: str | None = None) -> dict[str, int]:
    target_engine = (
        engine if database_url is None else create_database_engine(database_url)
    )
    Base.metadata.create_all(target_engine)
    settings = get_settings()
    tenant_id = str(settings.default_tenant_id)

    from sqlalchemy.orm import sessionmaker

    session_factory = sessionmaker(bind=target_engine)
    with session_factory() as session:
        tenant = session.get(Tenant, tenant_id)
        if tenant is None:
            tenant = Tenant(
                id=tenant_id,
                name="Demo Company",
                slug="demo-company",
                status="active",
            )
            session.add(tenant)

        owners = {}
        for index, (name, email) in enumerate(
            [
                ("Jordan Lee", "jordan@demo-company.example"),
                ("Morgan Chen", "morgan@demo-company.example"),
            ],
            start=1,
        ):
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
            ),
            (
                "Liam",
                "Davis",
                "liam.davis@blueyonder.example",
                "Blue Yonder Energy",
                "Energy",
                "Webinar",
                "QUALIFIED",
                91,
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
            ),
            (
                "Oliver",
                "Martinez",
                "oliver.martinez@litware.example",
                "Litware Finance",
                "Financial Services",
                "Email",
                "DISQUALIFIED",
                28,
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
            ),
        ]
        created_leads = 0
        for index, (
            first,
            last,
            email,
            company,
            industry,
            source,
            status,
            score,
        ) in enumerate(lead_rows):
            lead = (
                session.query(Lead).filter_by(tenant_id=tenant_id, email=email).first()
            )
            if lead is None:
                lead = Lead(
                    tenant_id=tenant_id,
                    first_name=first,
                    last_name=last,
                    email=email,
                    company=company,
                    industry=industry,
                    source=source,
                    status=status,
                    qualification_score=score,
                    owner_id=list(owners.values())[index % 2],
                )
                session.add(lead)
                created_leads += 1

        session.flush()
        if not session.query(FollowUp).filter_by(tenant_id=tenant_id).first():
            first_lead = session.query(Lead).filter_by(tenant_id=tenant_id).first()
            if first_lead:
                session.add(
                    FollowUp(
                        tenant_id=tenant_id,
                        lead_id=first_lead.id,
                        title="Introductory follow-up",
                        priority="medium",
                        status="OPEN",
                        due_at=__import__("datetime").datetime.now(
                            __import__("datetime").timezone.utc
                        ),
                    )
                )

        session.commit()
        return {
            "tenant_id": tenant_id,
            "created_or_existing_leads": len(lead_rows),
            "created_leads": created_leads,
        }


if __name__ == "__main__":
    print(seed())
