"""Markdown output rendering for risk assessments."""
from scia.core.risk import RiskAssessment

def render_markdown(assessment: RiskAssessment) -> str:
    """Render risk assessment as Markdown report."""
    # Determine classification emoji
    class_emoji = "🟢"
    if assessment.classification == "HIGH":
        class_emoji = "🔴"
    elif assessment.classification == "MEDIUM":
        class_emoji = "🟡"

    lines = [
        "# SCIA Impact Report",
        f"**Overall Risk Score:** {assessment.risk_score}/100",
        f"**Classification:** {class_emoji} {assessment.classification}",
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
        # Sort findings by severity (HIGH > MEDIUM > LOW)
        severity_priority = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_findings = sorted(
            assessment.findings,
            key=lambda f: severity_priority.get(
                f.severity.value if hasattr(f.severity, 'value') else str(f.severity),
                3
            )
        )

        for finding in sorted_findings:
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
                
                # Show tables with FKs referencing this table
                if impact.downstream_tables:
                    lines.append("")
                    lines.append("#### 🔗 Tables Referencing This Table (via Foreign Keys)")
                    lines.append("| Table | Schema | Critical |")
                    lines.append("|-------|--------|----------|")
                    for dep in impact.downstream_tables:
                        lines.append(
                            f"| {dep.name} | {dep.schema_name} | "
                            f"{'Yes' if dep.is_critical else 'No'} |"
                        )
                
                lines.append(f"- **Estimated Blast Radius:** {impact.estimated_blast_radius}")
            lines.append("")

    return "\n".join(lines)
