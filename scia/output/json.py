import json
from scia.core.risk import RiskAssessment

def render_json(assessment: RiskAssessment) -> str:
    """
    Renders risk assessment as a stable JSON string.
    """
    return json.dumps(assessment.to_dict(), indent=2)
