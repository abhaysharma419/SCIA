from typing import List
from scia.models.finding import Finding, Severity

class RiskAssessment:
    def __init__(self, findings: List[Finding]):
        self.findings = findings
        self.risk_score = sum(f.base_risk for f in findings)
        self.classification = self._classify(self.risk_score)

    def _classify(self, score: int) -> str:
        if score < 30:
            return "LOW"
        elif score < 70:
            return "MEDIUM"
        else:
            return "HIGH"

    def to_dict(self):
        return {
            "risk_score": self.risk_score,
            "classification": self.classification,
            "findings": [f.model_dump() for f in self.findings]
        }
