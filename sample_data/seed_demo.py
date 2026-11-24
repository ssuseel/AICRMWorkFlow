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
            ("Asha", "Patel", "asha.patel@northwind.example", "Northwind Manufacturing", "Manufacturing", "Website", "QUALIFIED", 82, "VP of Operations", "+1-206-555-0141"),
            ("Mateo", "Garcia", "mateo.garcia@contoso.example", "Contoso Logistics", "Logistics", "Referral", "NEW", 0, "Fleet Director", "+1-512-555-0188"),
            ("Priya", "Singh", "priya.singh@fabrikam.example", "Fabrikam Health", "Healthcare", "Conference", "CONTACTED", 65, "Director of Digital Health", "+1-617-555-0127"),
            ("Noah", "Williams", "noah.williams@tailspin.example", "Tailspin Software", "Technology", "CSV", "VALIDATED", 45, "Head of Customer Success", "+1-303-555-0164"),
            ("Eva", "Brown", "eva.brown@adatum.example", "Adatum Retail", "Retail", "Campaign", "NEW", 20, "E-commerce Manager", "+1-415-555-0192"),
            ("Liam", "Davis", "liam.davis@blueyonder.example", "Blue Yonder Energy", "Energy", "Webinar", "CUSTOMER", 91, "Chief Technology Officer", "+1-713-555-0136"),
            ("Sophia", "Wilson", "sophia.wilson@coho.example", "Coho Aviation", "Aviation", "Partner", "ENGAGED", 76, "VP of Commercial Operations", "+1-425-555-0173"),
            ("Oliver", "Martinez", "oliver.martinez@litware.example", "Litware Finance", "Financial Services", "Email", "SUPPRESSED", 28, "Finance Systems Analyst", "+1-212-555-0119"),
            ("Mia", "Anderson", "mia.anderson@proseware.example", "Proseware Media", "Media", "Website", "VALIDATED", 58, "Marketing Operations Lead", "+1-503-555-0158"),
            ("James", "Thomas", "james.thomas@wingtip.example", "Wingtip Toys", "Retail", "Campaign", "NEW", 12, "Procurement Coordinator", "+1-972-555-0161"),
            ("Isabella", "Moore", "isabella.moore@citypower.example", "City Power Utilities", "Utilities", "Referral", "CONTACTED", 68, "Grid Operations Manager", "+1-602-555-0198"),
            ("Benjamin", "Taylor", "benjamin.taylor@wideworld.example", "Wide World Importers", "Wholesale", "Conference", "QUALIFIED", 88, "Chief Revenue Officer", "+1-312-555-0105"),
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

        qualification_data = [
            ("asha.patel@northwind.example", 82, "High fit: plant modernization initiative", "Buying", "Budget confirmed", "Near-term", "Decision-maker", ["Schedule operations discovery", "Prepare solution comparison"]),
            ("mateo.garcia@contoso.example", 0, "No qualification evidence captured", "Unknown", "To be validated", "Not yet established", "Unknown", ["Request fleet size and timeline"]),
            ("priya.singh@fabrikam.example", 65, "Digital health team has an active evaluation", "Researching", "To be validated", "Near-term", "Influencer", ["Confirm budget and procurement owner"]),
            ("noah.williams@tailspin.example", 45, "Product interest confirmed; timeline is unclear", "Researching", "To be validated", "Not yet established", "Influencer", ["Ask for team size and rollout target"]),
            ("eva.brown@adatum.example", 20, "Early-stage retail campaign lead", "Unknown", "To be validated", "Not yet established", "Unknown", ["Nurture until a use case emerges"]),
            ("liam.davis@blueyonder.example", 91, "Strong budget, authority, need and timeline", "Buying", "Budget confirmed", "Near-term", "Decision-maker", ["Maintain executive relationship"]),
            ("sophia.wilson@coho.example", 76, "Meeting requested for commercial operations", "Buying", "Budget confirmed", "Near-term", "Decision-maker", ["Share the proposed rollout plan"]),
            ("oliver.martinez@litware.example", 28, "Unsubscribed after low-fit outreach", "Unknown", "Not applicable", "Not applicable", "Unknown", ["Keep suppressed"]),
            ("mia.anderson@proseware.example", 58, "Marketing use case matches platform capabilities", "Researching", "To be validated", "Next quarter", "Influencer", ["Validate campaign volume"]),
            ("james.thomas@wingtip.example", 12, "Small account with no confirmed need", "Unknown", "To be validated", "Not yet established", "Unknown", ["Nurture with educational content"]),
            ("isabella.moore@citypower.example", 68, "Operational reporting need and active interest", "Researching", "To be validated", "Near-term", "Influencer", ["Identify security review requirements"]),
            ("benjamin.taylor@wideworld.example", 88, "Executive sponsor and near-term buying window", "Buying", "Budget confirmed", "Near-term", "Decision-maker", ["Prepare commercial proposal"]),
        ]
        for email_address, score, assessment, intent, budget, timeline, authority, actions in qualification_data:
            lead = leads_by_email.get(email_address)
            if lead is None:
                continue
            existing = session.query(LeadQualification).filter_by(
                tenant_id=tenant_id, lead_id=lead.id
            ).first()
            if existing is None:
                session.add(
                    LeadQualification(
                        tenant_id=tenant_id,
                        lead_id=lead.id,
                        model_name="mock-qualification-v1",
                        prompt_version="demo-2026-11",
                        status="completed",
                        score=score,
                        business_requirements={"use_case": assessment, "company": lead.company},
                        customer_intent=intent,
                        budget_assessment=budget,
                        timeline_assessment=timeline,
                        authority_assessment=authority,
                        evidence={"summary": assessment},
                        missing_information=[] if score >= 80 else ["Budget", "Timeline", "Decision process"],
                        recommended_actions=actions,
                        created_at=now - timedelta(days=10),
                    )
                )

        email_specs = [
            ("asha.patel@northwind.example", "Northwind Manufacturing: operations discovery", "Hi Asha,\n\nFollowing our conversation, I would like to map Northwind's workflow automation priorities and identify a practical first rollout.\n\nWould Tuesday at 10:00 AM work for a 30-minute discovery session?\n\nBest,\nJordan", "SENT", -20),
            ("priya.singh@fabrikam.example", "Fabrikam Health: platform overview", "Hi Priya,\n\nThank you for meeting us at the conference. I am sending a concise overview of the capabilities relevant to your digital health program.\n\nCould we connect Thursday afternoon to discuss next steps?\n\nBest,\nMorgan", "SENT", -12),
            ("liam.davis@blueyonder.example", "Blue Yonder Energy: executive proposal", "Hi Liam,\n\nAs discussed, this proposal outlines the rollout, integration approach and success measures for the Blue Yonder pilot.\n\nPlease share any procurement requirements and we will prepare the formal order form.\n\nRegards,\nMorgan", "SENT", -8),
            ("sophia.wilson@coho.example", "Coho Aviation: 30-minute planning session", "Hi Sophia,\n\nI would be glad to help your operations team plan the commercial rollout. Here are proposed milestones for the first 60 days.\n\nAre you available for a planning session this week?\n\nBest,\nJordan", "PENDING_APPROVAL", -2),
            ("benjamin.taylor@wideworld.example", "Wide World Importers: commercial proposal", "Hi Benjamin,\n\nAttached is the tailored commercial proposal covering your import operations, reporting needs and phased deployment.\n\nI can walk through the assumptions with your team this week.\n\nBest,\nTaylor", "APPROVED", -1),
            ("mia.anderson@proseware.example", "Proseware Media: campaign workflow review", "Hi Mia,\n\nI enjoyed learning about your campaign operations. This draft summarizes a lightweight workflow review for your team.\n\nBest,\nTaylor", "DRAFT", 0),
            ("isabella.moore@citypower.example", "City Power Utilities: security and integration checklist", "Hi Isabella,\n\nThank you for the detailed call. Please find the integration and security checklist for our technical review.\n\nRegards,\nJordan", "DELIVERY_FAILED", -5),
        ]
        for email_address, subject, body, status, day_offset in email_specs:
            lead = leads_by_email.get(email_address)
            if lead is None:
                continue
            existing = session.query(Email).filter_by(
                tenant_id=tenant_id, lead_id=lead.id, subject=subject
            ).first()
            if existing is None:
                sent_at = now + timedelta(days=day_offset) if status == "SENT" else None
                session.add(
                    Email(
                        tenant_id=tenant_id,
                        lead_id=lead.id,
                        subject=subject,
                        body=body,
                        approved_subject=subject if status in {"APPROVED", "SENT"} else None,
                        approved_body=body if status in {"APPROVED", "SENT"} else None,
                        status=status,
                        approved_by_id=owners["Morgan Chen"] if status in {"APPROVED", "SENT"} else None,
                        approved_at=now + timedelta(days=day_offset) if status in {"APPROVED", "SENT"} else None,
                        provider="mock",
                        provider_message_id=f"mock-email-{email_address}-{abs(day_offset)}" if status == "SENT" else None,
                        thread_id=f"mock-thread-{email_address}" if status in {"SENT", "APPROVED"} else None,
                        idempotency_key=f"demo-email-{email_address}-{status}",
                        sent_at=sent_at,
                        created_at=now + timedelta(days=day_offset),
                    )
                )

        session.flush()
        response_specs = [
            ("asha.patel@northwind.example", "mock-response-asha", "meeting_request", "Asha requested a Tuesday operations discovery session.", "meeting interest", "Offer the requested meeting times", "high"),
            ("sophia.wilson@coho.example", "mock-response-sophia", "positive_interest", "Sophia is interested in the 60-day pilot and asked for a rollout plan.", "positive interest", "Prompt the account owner to prepare the plan", "high"),
            ("liam.davis@blueyonder.example", "mock-response-liam", "pricing_request", "Liam requested final pricing and procurement terms for the executive proposal.", "pricing interest", "Route the pricing request for human review", "high"),
            ("priya.singh@fabrikam.example", "mock-response-priya", "information_request", "Priya requested a technical overview for the digital health product team.", "information request", "Prepare a factual technical response", "medium"),
            ("oliver.martinez@litware.example", "mock-response-oliver", "unsubscribe", "Oliver asked to remove his address from future outreach.", "unsubscribe request", "Cancel follow-ups and suppress outreach", "urgent"),
        ]
        emails_by_lead = {
            email.lead_id: email
            for email in session.query(Email).filter_by(tenant_id=tenant_id).all()
        }
        for email_address, message_id, classification, summary, intent, action, priority in response_specs:
            lead = leads_by_email.get(email_address)
            if lead is None:
                continue
            existing = session.query(EmailResponse).filter_by(
                tenant_id=tenant_id, provider_message_id=message_id
            ).first()
            if existing is None:
                sent_email = emails_by_lead.get(lead.id)
                unsubscribed = classification == "unsubscribe"
                session.add(
                    EmailResponse(
                        tenant_id=tenant_id,
                        lead_id=lead.id,
                        email_id=sent_email.id if sent_email else None,
                        provider_message_id=message_id,
                        thread_id=sent_email.thread_id if sent_email else f"mock-thread-{email_address}",
                        from_address=email_address,
                        classification=classification,
                        summary=summary,
                        customer_intent=intent,
                        recommended_action=action,
                        priority=priority,
                        human_review_required=True,
                        unsubscribed=unsubscribed,
                        raw_content={"subject": summary, "body": summary},
                        created_at=now - timedelta(days=2),
                    )
                )

        followup_specs = [
            ("asha.patel@northwind.example", "Confirm Tuesday discovery session", "Call Asha to confirm the proposed operations discovery session.", "high", "OVERDUE", -2),
            ("mateo.garcia@contoso.example", "Research fleet operations priorities", "Gather fleet size, current process and rollout timeline.", "medium", "OPEN", 1),
            ("priya.singh@fabrikam.example", "Send technical overview", "Follow up with the digital health technical team after the overview.", "high", "SCHEDULED", 2),
            ("noah.williams@tailspin.example", "Validate success and rollout timeline", "Confirm the customer success team structure and renewal timing.", "medium", "OPEN", 4),
            ("liam.davis@blueyonder.example", "Prepare final commercial terms", "Coordinate pricing and legal requirements with Liam.", "urgent", "COMPLETED", 1),
            ("sophia.wilson@coho.example", "Prepare 60-day rollout plan", "Create a milestone plan for the requested commercial operations pilot.", "high", "OPEN", 3),
            ("mia.anderson@proseware.example", "Run campaign workflow review", "Review campaign volume and identify the first automation opportunity.", "medium", "SCHEDULED", 5),
            ("isabella.moore@citypower.example", "Complete security review", "Schedule a technical review with infrastructure and security stakeholders.", "high", "OVERDUE", -1),
            ("benjamin.taylor@wideworld.example", "Executive proposal review", "Hold a proposal review with Benjamin and his operations counterpart.", "urgent", "SCHEDULED", 1),
            ("eva.brown@adatum.example", "Qualify seasonal campaign need", "Ask about planned peak season and current campaign tooling.", "low", "OPEN", 6),
        ]
        for email_address, title, description, priority, status, day_offset in followup_specs:
            lead = leads_by_email.get(email_address)
            if lead is None:
                continue
            existing = session.query(FollowUp).filter_by(
                tenant_id=tenant_id, lead_id=lead.id, title=title
            ).first()
            if existing is None:
                session.add(
                    FollowUp(
                        tenant_id=tenant_id,
                        lead_id=lead.id,
                        owner_id=lead.owner_id,
                        title=title,
                        description=description,
                        priority=priority,
                        status=status,
                        due_at=now + timedelta(days=day_offset),
                        scheduled_at=now if status == "SCHEDULED" else None,
                        completed_at=now - timedelta(days=1) if status == "COMPLETED" else None,
                    )
                )

        for email_address in [
            "liam.davis@blueyonder.example",
            "benjamin.taylor@wideworld.example",
            "asha.patel@northwind.example",
            "sophia.wilson@coho.example",
            "priya.singh@fabrikam.example",
            "isabella.moore@citypower.example",
            "mia.anderson@proseware.example",
        ]:
            lead = leads_by_email.get(email_address)
            if lead is None:
                continue
            key = f"demo-crm-lead-{lead.id}"
            existing = session.query(CRMSyncRecord).filter_by(
                tenant_id=tenant_id, idempotency_key=key
            ).first()
            if existing is None:
                retry = email_address == "isabella.moore@citypower.example"
                session.add(
                    CRMSyncRecord(
                        tenant_id=tenant_id,
                        lead_id=lead.id,
                        provider="mock",
                        external_id=None if retry else f"mock-lead-{lead.id[:8]}",
                        entity_type="lead",
                        status="RETRY_SCHEDULED" if retry else "SYNCED",
                        attempt_count=2 if retry else 1,
                        next_retry_at=now + timedelta(hours=4) if retry else None,
                        last_error="Mock provider timeout" if retry else None,
                        idempotency_key=key,
                        created_at=now - timedelta(days=3),
                    )
                )

        if not session.query(CRMConnection).filter_by(
            tenant_id=tenant_id, provider="mock"
        ).first():
            session.add(
                CRMConnection(
                    tenant_id=tenant_id,
                    provider="mock",
                    status="active",
                    configuration={
                        "mode": "demo",
                        "environment": "sandbox",
                        "sync_direction": "local_to_mock_crm",
                    },
                )
            )

        for local_field, remote_field in {
            "first_name": "FirstName",
            "last_name": "LastName",
            "email": "Email",
            "phone": "Phone",
            "company": "Company",
            "title": "Title",
            "industry": "Industry",
            "source": "LeadSource",
        }.items():
            existing = session.query(CRMFieldMapping).filter_by(
                tenant_id=tenant_id,
                provider="mock",
                local_field=local_field,
            ).first()
            if existing is None:
                session.add(
                    CRMFieldMapping(
                        tenant_id=tenant_id,
                        provider="mock",
                        local_field=local_field,
                        remote_field=remote_field,
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
