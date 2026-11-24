"""Deterministic demonstration AI provider."""

from typing import Any

from src.domain.schemas import QualificationEvidence
from src.integrations.ai.base import AIProvider


class MockAIProvider(AIProvider):
    model_name = "mock-qualification-v1"

    def extract_qualification(
        self,
        lead_context: dict[str, Any],
        prompt_template: str,
    ) -> QualificationEvidence:
        del prompt_template
        company = str(lead_context.get("company") or "the customer")
        industry = str(lead_context.get("industry") or "")
        title = str(lead_context.get("title") or "")
        source = str(lead_context.get("source") or "")

        intent = "potential interest"
        if source.lower() in {"referral", "partner", "webinar"}:
            intent = "active interest"
        elif source.lower() in {"campaign", "csv"}:
            intent = "exploratory interest"

        requirements = [f"Confirm workflow and integration needs for {company}"]
        interest = [industry or "General CRM workflow"]
        missing = [
            "Budget range",
            "Purchase timeline",
            "Decision-making authority",
            "Specific business requirements",
        ]
        authority = (
            "Likely senior stakeholder"
            if any(
                word in title.lower()
                for word in ("director", "vp", "vice", "head", "chief")
            )
            else "Authority not confirmed"
        )

        return QualificationEvidence(
            business_requirements=requirements,
            customer_intent=intent,
            product_interest=interest,
            budget_assessment="Budget not confirmed",
            timeline_assessment="Purchase timeline not confirmed",
            authority_assessment=authority,
            evidence={
                "company": [company],
                "industry": [industry] if industry else [],
                "lead_source": [source] if source else [],
                "job_title": [title] if title else [],
            },
            missing_information=missing,
            recommended_actions=[
                "Schedule a discovery call",
                "Request budget and timeline",
                "Identify the decision-making process",
            ],
            summary=f"{company} has {intent}; additional discovery is needed.",
        )
