"""Tests for test_output."""
from scia.core.risk import RiskAssessment
from scia.output.json import render_json
from scia.output.markdown import render_markdown

def test_render_json(finding_factory):
    """Test function."""
    ra = RiskAssessment(findings=[finding_factory()])
    output = render_json(ra)
    assert '"risk_score": 70' in output # finding_factory default is 70

def test_render_markdown(finding_factory):
    """Test function."""
    ra = RiskAssessment(findings=[finding_factory()])
    output = render_markdown(ra)
    assert "# SCIA Impact Report" in output
    assert "🔴 COLUMN_REMOVED" in output

def test_render_markdown_empty():
    """Test function."""
    ra = RiskAssessment(findings=[])
    output = render_markdown(ra)
    assert "No impactful changes detected." in output
