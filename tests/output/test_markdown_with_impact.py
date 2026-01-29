"""Tests for Markdown rendering with impact details."""
from scia.core.risk import RiskAssessment
from scia.models.finding import Finding, FindingType, Severity, EnrichedFinding, ImpactDetail, DependencyObject
from scia.output.markdown import render_markdown

def test_render_markdown_with_impact():
    impact = ImpactDetail(
        direct_dependents=[
            DependencyObject(object_type="VIEW", name="view1", schema="public")
        ],
        estimated_blast_radius=1
    )
    
    finding = EnrichedFinding(
        finding_type=FindingType.COLUMN_REMOVED,
        severity=Severity.HIGH,
        base_risk=80,
        evidence={"table": "table1", "column": "col1"},
        description="Column 'col1' removed",
        impact_detail=impact
    )
    
    assessment = RiskAssessment([finding])
    output = render_markdown(assessment)
    
    assert "Downstream Impact" in output
    assert "| VIEW | view1 | public | No |" in output
    assert "**Estimated Blast Radius:** 1" in output

def test_render_markdown_without_impact():
    finding = Finding(
        finding_type=FindingType.COLUMN_REMOVED,
        severity=Severity.HIGH,
        base_risk=80,
        evidence={"table": "table1", "column": "col1"},
        description="Column 'col1' removed"
    )
    
    assessment = RiskAssessment([finding])
    output = render_markdown(assessment)
    
    assert "Downstream Impact" not in output
    assert "table1" in output
