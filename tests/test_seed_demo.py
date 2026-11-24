from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from sample_data.seed_demo import seed
from src.db.models import (
    CRMConnection,
    CRMFieldMapping,
    CRMSyncRecord,
    Email,
    EmailResponse,
    FollowUp,
    Lead,
    LeadQualification,
)


def test_seed_demo_uses_valid_qualification_states_and_is_idempotent(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'demo.db'}"

    first_result = seed(database_url)
    engine = create_engine(database_url)
    with sessionmaker(bind=engine)() as session:
        lead = (
            session.query(Lead)
            .filter_by(
                tenant_id=first_result["tenant_id"],
                email="asha.patel@northwind.example",
            )
            .one()
        )
        qualification = (
            session.query(LeadQualification)
            .filter_by(
                tenant_id=first_result["tenant_id"],
                lead_id=lead.id,
            )
            .one()
        )
        lead.qualification_status = "qualified"
        qualification.status = "completed"
        session.commit()

    second_result = seed(database_url)

    assert first_result["created_leads"] == 12
    assert second_result["created_leads"] == 0

    with sessionmaker(bind=engine)() as session:
        leads = session.query(Lead).filter_by(tenant_id=first_result["tenant_id"]).all()
        qualifications = (
            session.query(LeadQualification)
            .filter_by(tenant_id=first_result["tenant_id"])
            .all()
        )

        assert len(leads) == len(qualifications) == 12
        assert all(
            qualification.status
            == (
                "QUALIFIED"
                if qualification.score >= 70
                else "DISQUALIFIED"
                if qualification.score < 40
                else "QUALIFICATION_PENDING"
            )
            for qualification in qualifications
        )
        assert all(
            lead.qualification_status
            in {
                "QUALIFIED",
                "DISQUALIFIED",
                "QUALIFICATION_PENDING",
            }
            for lead in leads
        )
        assert all(
            lead.qualification_status
            == next(
                qualification.status
                for qualification in qualifications
                if qualification.lead_id == lead.id
            )
            for lead in leads
        )

        expected_counts = {
            Email: 7,
            EmailResponse: 5,
            FollowUp: 10,
            CRMSyncRecord: 7,
            CRMConnection: 1,
            CRMFieldMapping: 8,
        }
        for model, expected_count in expected_counts.items():
            count = (
                session.query(func.count(model.id))
                .filter_by(tenant_id=first_result["tenant_id"])
                .scalar()
            )
            assert count == expected_count
