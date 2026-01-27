"""Markdown output rendering for risk assessments."""
from scia.core.risk import RiskAssessment

def render_markdown(assessment: RiskAssessment) -> str:
    """Render risk assessment as Markdown report."""
    lines = [
        "# SCIA Impact Report",
        f"**Risk Score:** {assessment.risk_score}",
        f"**Classification:** {assessment.classification}",
        "",
        "## Findings",
        ""
    ]

    if not assessment.findings:
        lines.append("No impactful changes detected.")
    else:
        for finding in assessment.findings:
            if finding.severity == "HIGH":
                emoji = "🔴"
            elif finding.severity == "MEDIUM":
                emoji = "🟡"
            else:
                emoji = "🟢"
            lines.append(f"### {emoji} {finding.finding_type}")
            lines.append(f"- **Severity:** {finding.severity}")
            lines.append(f"- **Description:** {finding.description}")
            lines.append(f"- **Evidence:** `{finding.evidence}`")
            lines.append("")

    return "\n".join(lines)
