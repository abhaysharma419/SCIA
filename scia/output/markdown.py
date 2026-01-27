from scia.core.risk import RiskAssessment

def render_markdown(assessment: RiskAssessment) -> str:
    """
    Renders risk assessment as a human-readable Markdown report.
    """
    lines = [
        f"# SCIA Impact Report",
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
            emoji = "🔴" if finding.severity == "HIGH" else "🟡" if finding.severity == "MEDIUM" else "🟢"
            lines.append(f"### {emoji} {finding.finding_type}")
            lines.append(f"- **Severity:** {finding.severity}")
            lines.append(f"- **Description:** {finding.description}")
            lines.append(f"- **Evidence:** `{finding.evidence}`")
            lines.append("")
            
    return "\n".join(lines)
