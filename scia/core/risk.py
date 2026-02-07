"""Risk assessment and classification."""
from typing import List, Optional

from scia.models.finding import Finding, Severity

class RiskAssessment:  # pylint: disable=too-few-public-methods
    """Aggregate findings into risk classification."""

    def __init__(self, findings: List[Finding], warnings: Optional[List[str]] = None):
        """Initialize with findings and compute risk score."""
        self.findings = findings
        self.warnings = warnings or []
        
        # Calculate raw total from individual finding risk scores
        raw_total = sum(f.risk_score for f in findings if f.risk_score is not None)
        
        # Normalize to 0-100% using a saturation curve
        # Formula: 100 * (raw / (raw + K)) where K is the sensitivity constant.
        # K=150 means a raw score of 150 results in a 50% normalized risk.
        # This ensures 100% is only approached in "catastrophic" scenarios.
        if raw_total == 0:
            self.risk_score = 0
        else:
            sensitivity = 100
            self.risk_score = int(100 * (raw_total / (raw_total + sensitivity)))
            
        self.classification = self._classify(self.risk_score)

    def _classify(self, score: int) -> str:
        """Classify risk based on normalized 0-100 score."""
        if score < 15:
            return "LOW"
        
        # Check if any finding has HIGH severity
        has_high_finding = any(f.severity == Severity.HIGH for f in self.findings)
        
        if score < 40:
            return "MEDIUM"
        
        # If score >= 40 but no individual HIGH finding, cap at MEDIUM
        if not has_high_finding:
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
