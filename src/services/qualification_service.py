"""AI qualification orchestration and deterministic scoring."""

from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.models import Lead, LeadQualification
from src.domain.schemas import QualificationEvidence, QualificationResult
from src.integrations.ai.base import AIProvider
from src.integrations.ai.factory import create_ai_provider

QUALIFICATION_PROMPT_VERSION = "qualification-v1"


class QualificationService:
    def __init__(
        self,
        session: Session,
        tenant_id: str,
        provider: AIProvider | None = None,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.provider = provider or create_ai_provider(get_settings().ai_provider)

    def _load_prompt(self) -> str:
        prompt_path = Path("prompts/lead_qualification.txt")
        if not prompt_path.exists():
            raise FileNotFoundError("Qualification prompt file is missing")
        return prompt_path.read_text(encoding="utf-8")

    @staticmethod
    def calculate_score(evidence: QualificationEvidence) -> int:
        score = 10
        intent = evidence.customer_intent.lower()
        if "active" in intent:
            score += 25
        elif "potential" in intent:
            score += 15
        elif "exploratory" in intent:
            score += 8

        if evidence.business_requirements:
            score += 15
        if evidence.product_interest:
            score += 10

        budget = evidence.budget_assessment.lower()
        if any(word in budget for word in ("confirmed", "allocated", "approved")):
            score += 15
        elif "not confirmed" not in budget and "unknown" not in budget:
            score += 5

        timeline = evidence.timeline_assessment.lower()
        if any(word in timeline for word in ("immediate", "30", "quarter", "weeks")):
            score += 15
        elif "not confirmed" not in timeline and "unknown" not in timeline:
            score += 5

        authority = evidence.authority_assessment.lower()
        if "senior" in authority or "decision" in authority:
            score += 15
        elif "not confirmed" not in authority and "unknown" not in authority:
            score += 8

        evidence_count = sum(1 for values in evidence.evidence.values() if values)
        score += min(evidence_count * 2, 10)
        return max(0, min(score, 100))

    def qualify(self, lead_id: str) -> QualificationResult:
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

        lead_context: dict[str, Any] = {
            "id": lead.id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "email": lead.email,
            "company": lead.company,
            "title": lead.title,
            "industry": lead.industry,
            "source": lead.source,
        }
        used_fallback = False
        try:
            prompt = self._load_prompt()
            evidence = self.provider.extract_qualification(
                lead_context,
                prompt,
            )
            evidence = QualificationEvidence.model_validate(evidence)
        except (FileNotFoundError, ValidationError, RuntimeError, TimeoutError):
            used_fallback = True
            evidence = QualificationEvidence(
                customer_intent="qualification unavailable",
                summary="AI qualification unavailable; conservative fallback applied.",
                missing_information=[
                    "Business requirements",
                    "Budget",
                    "Purchase timeline",
                    "Decision authority",
                ],
                recommended_actions=["Manually validate lead before outreach"],
            )

        score = self.calculate_score(evidence)
        if used_fallback:
            status = "QUALIFICATION_PENDING"
        else:
            status = (
                "QUALIFIED"
                if score >= 70
                else "DISQUALIFIED"
                if score < 40
                else "QUALIFICATION_PENDING"
            )

        qualification = LeadQualification(
            tenant_id=self.tenant_id,
            lead_id=lead.id,
            model_name=getattr(self.provider, "model_name", "unavailable"),
            prompt_version=QUALIFICATION_PROMPT_VERSION,
            status=status,
            score=score,
            business_requirements={"items": evidence.business_requirements},
            customer_intent=evidence.customer_intent,
            product_interest={"items": evidence.product_interest},
            budget_assessment=evidence.budget_assessment,
            timeline_assessment=evidence.timeline_assessment,
            authority_assessment=evidence.authority_assessment,
            evidence=evidence.evidence,
            missing_information=evidence.missing_information,
            recommended_actions=evidence.recommended_actions,
        )
        lead.qualification_score = score
        lead.qualification_status = status
        lead.status = status
        self.session.add(qualification)
        self.session.commit()
        self.session.refresh(lead)
        self.session.refresh(qualification)
        return QualificationResult(
            lead_id=lead.id,
            score=score,
            status=status,
            evidence=evidence,
            model_name=qualification.model_name,
            prompt_version=qualification.prompt_version,
        )
