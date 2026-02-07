"""Risk assessment and classification."""
from typing import List, Optional

from scia.models.finding import Finding

class RiskAssessment:  # pylint: disable=too-few-public-methods
    """Aggregate findings into risk classification."""

    def __init__(self, findings: List[Finding], warnings: Optional[List[str]] = None):
        """Initialize with findings and compute risk score."""
        self.findings = findings
        self.warnings = warnings or []
        self.risk_score = sum(f.base_risk for f in findings)
        self.classification = self._classify(self.risk_score)

    def _classify(self, score: int) -> str:
        """Classify risk based on score."""
        if score < 30:
            return "LOW"
        if score < 70:
            return "MEDIUM"
        return "HIGH"

    def to_dict(self):
        """Convert to dictionary representation."""
        return {
            "risk_score": self.risk_score,
            "classification": self.classification,
            "findings": [f.model_dump() for f in self.findings],
            "warnings": self.warnings
        }
