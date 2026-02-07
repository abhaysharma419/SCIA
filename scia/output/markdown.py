"""Markdown output rendering for risk assessments."""
from scia.core.risk import RiskAssessment

def render_markdown(assessment: RiskAssessment) -> str:
    """Render risk assessment as Markdown report."""
    lines = [
        "# SCIA Impact Report",
        f"**Overall Risk Score:** {assessment.risk_score}/100",
        f"**Classification:** {assessment.classification}",
        ""
    ]
    
    if assessment.warnings:
        lines.append("### ⚠️ Warnings")
        for warning in assessment.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.extend([
        "## Findings",
        ""
    ])

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
            lines.append(f"### {emoji} {finding.finding_type.value} (Score: {finding.risk_score})")
            lines.append(f"- **Severity:** {finding.severity.value}")
            lines.append(f"- **Description:** {finding.description}")
            lines.append(f"- **Evidence:** `{finding.evidence}`")

            # Add Impact Detail if present (EnrichedFinding)
            if hasattr(finding, 'impact_detail') and finding.impact_detail:
                impact = finding.impact_detail
                lines.append("")
                lines.append("#### 📉 Downstream Impact")
                if impact.direct_dependents:
                    lines.append("| Object Type | Name | Schema | Critical |")
                    lines.append("|-------------|------|--------|----------|")
                    for dep in impact.direct_dependents:
                        lines.append(
                            f"| {dep.object_type} | {dep.name} | "
                            f"{dep.schema_name} | {'Yes' if dep.is_critical else 'No'} |"
                        )
                else:
                    lines.append("No direct downstream dependents identified.")
                lines.append(f"- **Estimated Blast Radius:** {impact.estimated_blast_radius}")
            lines.append("")

    return "\n".join(lines)
