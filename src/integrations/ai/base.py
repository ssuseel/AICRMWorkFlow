"""AI qualification provider interface."""

from abc import ABC, abstractmethod
from typing import Any

from src.domain.schemas import QualificationEvidence


class AIProvider(ABC):
    @abstractmethod
    def extract_qualification(
        self,
        lead_context: dict[str, Any],
        prompt_template: str,
    ) -> QualificationEvidence:
        """Extract structured qualification evidence from lead context."""
