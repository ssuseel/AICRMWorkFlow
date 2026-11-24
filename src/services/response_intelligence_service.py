"""Incoming response classification and follow-up cancellation."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.db.models import Email, EmailResponse, FollowUp, Lead
from src.domain.schemas import IncomingEmail, ResponseClassification

CLASSIFICATIONS = (
    "positive_interest",
    "information_request",
    "pricing_request",
    "objection",
    "meeting_request",
    "not_interested",
    "out_of_office",
    "complaint",
    "unsubscribe",
)


class ResponseIntelligenceService:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def classify(self, incoming: IncomingEmail) -> ResponseClassification:
        text = f"{incoming.subject}\n{incoming.body}".lower()
        if any(word in text for word in ("unsubscribe", "remove me", "opt out")):
            classification = "unsubscribe"
            priority = "urgent"
            intent = "unsubscribe request"
            action = "Cancel follow-ups and add the address to suppression"
            unsubscribed = True
        elif any(
            word in text for word in ("not interested", "no thanks", "do not contact")
        ):
            classification = "not_interested"
            priority = "high"
            intent = "not interested"
            action = "Cancel follow-ups and suppress future outreach"
            unsubscribed = False
        elif "meeting" in text or "schedule" in text or "call" in text:
            classification = "meeting_request"
            priority = "high"
            intent = "meeting interest"
            action = "Offer available times for human review"
            unsubscribed = False
        elif "price" in text or "pricing" in text or "cost" in text:
            classification = "pricing_request"
            priority = "high"
            intent = "pricing interest"
            action = "Route pricing request for human response"
            unsubscribed = False
        elif "complaint" in text or "unhappy" in text:
            classification = "complaint"
            priority = "urgent"
            intent = "customer concern"
            action = "Escalate to customer success"
            unsubscribed = False
        elif "information" in text or "details" in text or "learn more" in text:
            classification = "information_request"
            priority = "medium"
            intent = "information request"
            action = "Prepare a factual response for approval"
            unsubscribed = False
        elif "objection" in text or "concern" in text:
            classification = "objection"
            priority = "high"
            intent = "objection"
            action = "Review concern and prepare a human response"
            unsubscribed = False
        elif "out of office" in text or "away until" in text:
            classification = "out_of_office"
            priority = "low"
            intent = "temporarily unavailable"
            action = "Reschedule follow-up after the stated absence"
            unsubscribed = False
        else:
            classification = "positive_interest"
            priority = "high"
            intent = "positive interest"
            action = "Prompt a lead owner to review and engage"
            unsubscribed = False

        return ResponseClassification(
            provider_message_id=incoming.provider_message_id,
            thread_id=incoming.thread_id,
            from_address=incoming.from_address,
            classification=classification,
            summary=incoming.subject.strip()
            or incoming.body.strip()[:240]
            or "Customer response received",
            customer_intent=intent,
            recommended_action=action,
            priority=priority,
            human_review_required=classification not in {"out_of_office"},
            unsubscribed=unsubscribed,
        )

    def ingest(self, incoming: IncomingEmail) -> EmailResponse:
        existing = (
            self.session.query(EmailResponse)
            .filter(
                EmailResponse.tenant_id == self.tenant_id,
                EmailResponse.provider_message_id == incoming.provider_message_id,
            )
            .first()
        )
        if existing:
            return existing

        classification = self.classify(incoming)
        lead = (
            self.session.query(Lead)
            .filter(
                Lead.tenant_id == self.tenant_id,
                Lead.email.ilike(incoming.from_address.strip()),
                Lead.deleted_at.is_(None),
            )
            .first()
        )
        email = (
            self.session.query(Email)
            .filter(
                Email.tenant_id == self.tenant_id,
                Email.thread_id == incoming.thread_id,
            )
            .first()
        )
        response = EmailResponse(
            tenant_id=self.tenant_id,
            lead_id=lead.id if lead else None,
            email_id=email.id if email else None,
            provider_message_id=incoming.provider_message_id,
            thread_id=incoming.thread_id,
            from_address=incoming.from_address,
            classification=classification.classification,
            summary=classification.summary,
            customer_intent=classification.customer_intent,
            recommended_action=classification.recommended_action,
            priority=classification.priority,
            human_review_required=classification.human_review_required,
            unsubscribed=classification.unsubscribed,
            raw_content={"subject": incoming.subject, "body": incoming.body},
        )
        self.session.add(response)

        if lead:
            lead.status = (
                "SUPPRESSED"
                if classification.unsubscribed
                or classification.classification == "not_interested"
                else "ENGAGED"
            )
            if classification.unsubscribed or classification.classification in {
                "not_interested",
                "positive_interest",
                "meeting_request",
                "pricing_request",
                "objection",
                "complaint",
            }:
                for follow_up in (
                    self.session.query(FollowUp)
                    .filter(
                        FollowUp.tenant_id == self.tenant_id,
                        FollowUp.lead_id == lead.id,
                        FollowUp.status.in_(["OPEN", "SCHEDULED", "OVERDUE"]),
                    )
                    .all()
                ):
                    follow_up.status = "CANCELLED"
                    follow_up.cancelled_at = datetime.now(UTC)
                    follow_up.cancellation_reason = (
                        "Customer unsubscribed"
                        if classification.unsubscribed
                        else f"Customer response: {classification.classification}"
                    )
        self.session.commit()
        self.session.refresh(response)
        return response
