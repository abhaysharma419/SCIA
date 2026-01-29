import pytest
from unittest.mock import patch
from scia.core.analyze import analyze

@pytest.mark.asyncio
async def test_analyze_pipeline(table_factory, column_factory):
    """Test function."""
    # Scenario: One column removed
    col1 = column_factory(column_name="C1")
    col2 = column_factory(column_name="C2")

    before = [table_factory(columns=[col1, col2])]
    after = [table_factory(columns=[col1])]

    assessment = await analyze(before, after)

    assert assessment.risk_score == 80
    assert assessment.classification == "HIGH"
    assert len(assessment.findings) == 1
    assert assessment.findings[0].finding_type == "COLUMN_REMOVED"

@pytest.mark.asyncio
async def test_analyze_multiple_findings(table_factory, column_factory):
    """Test function."""
    # Scenario: One column removed (HIGH), one type change (MEDIUM)
    col1_before = column_factory(column_name="C1", data_type="INT")
    col1_after = column_factory(column_name="C1", data_type="STRING")
    col2 = column_factory(column_name="C2")

    before = [table_factory(columns=[col1_before, col2])]
    after = [table_factory(columns=[col1_after])]

    assessment = await analyze(before, after)

    # 80 (removed C2) + 40 (type change C1) + 50 (potential breakage) = 170
    assert assessment.risk_score == 170
    assert assessment.classification == "HIGH"
    assert len(assessment.findings) == 3

@pytest.mark.asyncio
async def test_analyze_risk_integration(table_factory):
    """Test function."""
    # Scenario: No changes
    table = table_factory()
    assessment = await analyze([table], [table])

    assert assessment.risk_score == 0
    assert assessment.classification == "LOW"

@pytest.mark.asyncio
@patch("scia.core.analyze.extract_signals")
async def test_analyze_graceful_sql_degradation(mock_extract, table_factory, column_factory):
    """Test function."""
    # Mock extract_signals to fail (return empty or trigger error)
    mock_extract.return_value = {}

    col1 = column_factory(column_name="C1")
    before = [table_factory(columns=[col1])]
    after = [table_factory(columns=[])]

    # Even if SQL extraction fails somehow (or returns nothing),
    # the schema-based analysis should still work.
    assessment = await analyze(before, after, sql_definitions={"q1": "SELECT * FROM T"})

    assert assessment.risk_score == 80
    assert len(assessment.findings) == 1

@pytest.mark.asyncio
async def test_analyze_sql_signals_parameter(table_factory, column_factory):
    """Test function."""
    col1 = column_factory(column_name="C1")
    before = [table_factory(columns=[col1])]
    after = [table_factory(columns=[])]

    # No SQL signals
    assessment_no_sql = await analyze(before, after, sql_definitions=None)
    assert assessment_no_sql.risk_score == 80

    # With SQL signals
    assessment_with_sql = await analyze(
        before, after, sql_definitions={"q1": "SELECT C1 FROM TEST_TABLE"}
    )
    assert assessment_with_sql.risk_score == 80
