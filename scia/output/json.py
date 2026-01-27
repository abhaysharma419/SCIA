"""JSON output rendering for risk assessments."""
import json  # pylint: disable=import-self,redefined-builtin

from scia.core.risk import RiskAssessment

def render_json(assessment: RiskAssessment) -> str:
    """Render risk assessment as JSON string."""
    # pylint: disable=no-member
    return json.dumps(assessment.to_dict(), indent=2)
