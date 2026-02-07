"""Tests to fill coverage gaps."""
import logging
from scia.input.resolver import _detect_format
from scia.sql.ddl_parser import parse_ddl_to_schema
from scia.core.risk import RiskAssessment
from scia.models.finding import Finding, FindingType, Severity, EnrichedFinding, ImpactDetail
from scia.output.markdown import render_markdown

def test_detect_format_file_existence(tmp_path):
    """Test _detect_format with real files to cover path existence branches."""
    # File with .json exists
    j = tmp_path / "test.json"
    j.touch()
    assert _detect_format(str(j)) == "json"

    # File with .sql exists
    s = tmp_path / "test.sql"
    s.touch()
    assert _detect_format(str(s)) == "sql"

    # File exists without extension (defaults to json)
    n = tmp_path / "noext"
    n.touch()
    assert _detect_format(str(n)) == "json"

def test_markdown_with_warnings_and_medium():
    """Test markdown rendering with warnings and MEDIUM severity."""
    finding = Finding(
        finding_type=FindingType.COLUMN_REMOVED,
        severity=Severity.MEDIUM,
        base_risk=50,
        evidence={"table": "T1", "column": "C1"},
        description="Desc"
    )
    assessment = RiskAssessment(findings=[finding], warnings=["Warning 1"])
    output = render_markdown(assessment)
    assert "Warning 1" in output
    assert "🟡" in output

def test_markdown_with_impact_no_dependents():
    """Test markdown rendering for EnrichedFinding with empty dependents."""
    impact = ImpactDetail(direct_dependents=[], estimated_blast_radius=0)
    finding = EnrichedFinding(
        finding_type=FindingType.COLUMN_REMOVED,
        severity=Severity.LOW,
        base_risk=10,
        evidence={"table": "T1", "column": "C1"},
        description="Desc",
        impact_detail=impact
    )
    assessment = RiskAssessment(findings=[finding])
    output = render_markdown(assessment)
    assert "No direct downstream dependents identified" in output
    assert "🟢" in output

def test_ddl_parser_failed_alter(caplog):  # pylint: disable=unused-argument
    """Test failed extraction of ALTER TABLE."""
    ddl = "ALTER TABLE;"
    parse_ddl_to_schema(ddl)
    # Should not crash

def test_ddl_parser_unsupported_stmt(caplog):
    """Test logging of unsupported statements in DDL parser."""
    with caplog.at_level(logging.DEBUG):
        ddl = "SELECT 1;"
        parse_ddl_to_schema(ddl)
        assert "Skipping unsupported statement type" in caplog.text

def test_ddl_parser_invalid_create(caplog):  # pylint: disable=unused-argument
    """Test failed extraction of CREATE TABLE."""
    # Create statement without schema/table
    ddl = "CREATE TABLE;"
    parse_ddl_to_schema(ddl)
    # Should not crash

def test_ddl_parser_alter_table_not_found(caplog):
    """Test ALTER TABLE when table is not in schemas."""
    with caplog.at_level(logging.DEBUG):
        ddl = "ALTER TABLE NON_EXISTENT ADD COLUMN C1 INT;"
        parse_ddl_to_schema(ddl)
        assert "not found for ALTER" in caplog.text
