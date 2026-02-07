"""Edge case stress tests for SCIA."""
import json
import time
from unittest.mock import MagicMock, patch
import pytest
from scia.cli.main import run_analyze
from scia.models.schema import TableSchema, ColumnSchema

# pylint: disable=too-few-public-methods,too-many-instance-attributes

class MockArgs:
    """Mock arguments for the CLI."""
    def __init__(self, **kwargs):
        self.before = kwargs.get('before')
        self.after = kwargs.get('after')
        self.warehouse = kwargs.get('warehouse')
        self.conn_file = kwargs.get('conn_file')
        self.dependency_depth = kwargs.get('dependency_depth', 3)
        self.include_upstream = kwargs.get('include_upstream', True)
        self.include_downstream = kwargs.get('include_downstream', True)
        self.format = kwargs.get('format', 'json')
        self.fail_on = kwargs.get('fail_on', 'HIGH')

@pytest.mark.asyncio
async def test_circular_view_dependencies(tmp_path, capsys):  # pylint: disable=unused-argument
    """Test that circular view dependencies don't cause infinite loops."""
    # A -> B -> A
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    schema = [TableSchema(schema_name="S", table_name="T1", columns=[
        ColumnSchema(
            schema_name="S", table_name="T1", column_name="C1",
            data_type="INT", is_nullable=True, ordinal_position=1
        )
    ])]
    schema_after = [TableSchema(schema_name="S", table_name="OTHER", columns=[
        ColumnSchema(
            schema_name="S", table_name="OTHER", column_name="C1",
            data_type="INT", is_nullable=True, ordinal_position=1
        )
    ])]
    before.write_text(json.dumps([s.model_dump() for s in schema]), encoding="utf-8")
    after.write_text(json.dumps([s.model_dump() for s in schema_after]), encoding="utf-8")

    args = MockArgs(
        before=str(before),
        after=str(after),
        warehouse="snowflake"
    )

    with patch("scia.cli.main.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_adapter.fetch_views.return_value = {
            "VIEW_A": "SELECT * FROM VIEW_B",
            "VIEW_B": "SELECT * FROM VIEW_A"
        }
        mock_adapter.parse_table_references.side_effect = lambda sql: [sql.split()[-1]]
        mock_get_adapter.return_value = mock_adapter

        # This should complete without infinite recursion
        with pytest.raises(SystemExit):
            await run_analyze(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data["findings"]) >= 1

@pytest.mark.asyncio
async def test_deep_dependency_chain(tmp_path, capsys):
    """Test that deep dependency chains are honored up to max_depth."""
    # T1 -> V1 -> V2 -> V3 -> V4
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    schema = [TableSchema(schema_name="S", table_name="T1", columns=[
        ColumnSchema(schema_name="S", table_name="T1", column_name="C1", data_type="INT", is_nullable=True, ordinal_position=1)
    ])]
    schema_after = [TableSchema(schema_name="S", table_name="OTHER", columns=[
        ColumnSchema(schema_name="S", table_name="OTHER", column_name="C1", data_type="INT", is_nullable=True, ordinal_position=1)
    ])]
    before.write_text(json.dumps([s.model_dump() for s in schema]), encoding="utf-8")
    after.write_text(json.dumps([s.model_dump() for s in schema_after]), encoding="utf-8")

    # Test with depth 2
    args = MockArgs(
        before=str(before),
        after=str(after),
        warehouse="snowflake",
        dependency_depth=2
    )

    with patch("scia.cli.main.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_adapter.fetch_views.return_value = {
            "V1": "SELECT * FROM T1",
            "V2": "SELECT * FROM V1",
            "V3": "SELECT * FROM V2",
            "V4": "SELECT * FROM V3"
        }
        def mock_parse(sql):
            return [sql.split()[-1]]
        mock_adapter.parse_table_references.side_effect = mock_parse
        mock_get_adapter.return_value = mock_adapter

        with pytest.raises(SystemExit):
            await run_analyze(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        finding = data["findings"][0]
        # At depth 2, we should find V1 and V2
        names = [d["name"] for d in finding["impact_detail"]["direct_dependents"]]
        assert "V1" in names
        assert "V2" in names
        assert "V3" not in names

@pytest.mark.asyncio
async def test_large_schema_performance(tmp_path, capsys):  # pylint: disable=unused-argument
    """Test performance with a large number of tables and columns."""
    before = tmp_path / "before_large.json"
    after = tmp_path / "after_large.json"

    num_tables = 50
    cols_per_table = 20

    schema = []
    for i in range(num_tables):
        cols = [
            ColumnSchema(
                schema_name="S", table_name=f"T{i}", column_name=f"C{j}",
                data_type="INT", is_nullable=True, ordinal_position=j+1
            )
            for j in range(cols_per_table)
        ]
        schema.append(TableSchema(schema_name="S", table_name=f"T{i}", columns=cols))

    # Change one column in one table
    schema_after = [s.model_dump() for s in schema]
    schema_after[0]["columns"][0]["data_type"] = "STRING"

    before.write_text(json.dumps([s.model_dump() for s in schema]), encoding="utf-8")
    after.write_text(json.dumps(schema_after), encoding="utf-8")

    args = MockArgs(before=str(before), after=str(after))

    start = time.time()
    with pytest.raises(SystemExit):
        await run_analyze(args)
    end = time.time()

    assert end - start < 5.0 # Should be fast

@pytest.mark.asyncio
async def test_special_characters_identifiers(tmp_path, capsys):
    """Test identifiers with special characters."""
    before = tmp_path / "before_spec.json"
    after = tmp_path / "after_spec.json"

    # Table with emoji or spaces (if supported by identifiers)
    table_name = '"Table With Space"'
    col_name = '"Col-With-Dash"'

    schema = [TableSchema(schema_name="S", table_name=table_name, columns=[
        ColumnSchema(schema_name="S", table_name=table_name, column_name=col_name, data_type="INT", is_nullable=True, ordinal_position=1)
    ])]
    schema_after = [TableSchema(schema_name="S", table_name=table_name, columns=[
        ColumnSchema(schema_name="S", table_name=table_name, column_name=col_name, data_type="STRING", is_nullable=True, ordinal_position=1)
    ])]

    before.write_text(json.dumps([s.model_dump() for s in schema]), encoding="utf-8")
    after.write_text(json.dumps([s.model_dump() for s in schema_after]), encoding="utf-8")

    args = MockArgs(before=str(before), after=str(after))

    with pytest.raises(SystemExit):
        await run_analyze(args)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data["findings"]) >= 1
    assert data["findings"][0]["evidence"]["column"] == col_name

@pytest.mark.asyncio
async def test_empty_schema_no_findings(tmp_path, capsys):
    """Test that comparing empty schemas results in no findings."""
    before = tmp_path / "before_empty.json"
    after = tmp_path / "after_empty.json"
    before.write_text("[]", encoding="utf-8")
    after.write_text("[]", encoding="utf-8")

    args = MockArgs(before=str(before), after=str(after))

    with pytest.raises(SystemExit) as excinfo:
        await run_analyze(args)

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["findings"] == []
    assert data["risk_score"] == 0
    assert data["classification"] == "LOW"

@pytest.mark.asyncio
async def test_no_changes_low_risk(tmp_path, capsys):
    """Test that identical schemas result in 0 score and LOW classification."""
    before = tmp_path / "before_same.json"
    after = tmp_path / "after_same.json"
    schema = [TableSchema(schema_name="S", table_name="T1", columns=[
        ColumnSchema(schema_name="S", table_name="T1", column_name="C1", data_type="INT", is_nullable=True, ordinal_position=1)
    ])]
    before.write_text(json.dumps([s.model_dump() for s in schema]), encoding="utf-8")
    after.write_text(json.dumps([s.model_dump() for s in schema]), encoding="utf-8")

    args = MockArgs(before=str(before), after=str(after))

    with pytest.raises(SystemExit):
        await run_analyze(args)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data["findings"]) == 0
    assert data["risk_score"] == 0
    assert data["classification"] == "LOW"

@pytest.mark.asyncio
async def test_multiple_high_risk_aggregation(tmp_path, capsys):
    """Test that multiple HIGH risk findings aggregate correctly (score should be high)."""
    # Create schema with multiple breaking changes
    # 1. Column type change (HIGH/MEDIUM depending on rules)
    # 2. Dropped column (HIGH/MEDIUM)
    before = tmp_path / "before_high.json"
    after = tmp_path / "after_high.json"

    s_before = [TableSchema(schema_name="S", table_name="T1", columns=[
        ColumnSchema(schema_name="S", table_name="T1", column_name="C1", data_type="INT", is_nullable=True, ordinal_position=1),
        ColumnSchema(schema_name="S", table_name="T1", column_name="C2", data_type="INT", is_nullable=True, ordinal_position=2)
    ])]

    s_after = [TableSchema(schema_name="S", table_name="T1", columns=[
        ColumnSchema(schema_name="S", table_name="T1", column_name="C1", data_type="VARCHAR", is_nullable=True, ordinal_position=1)
        # C2 is dropped
    ])]

    before.write_text(json.dumps([s.model_dump() for s in s_before]), encoding="utf-8")
    after.write_text(json.dumps([s.model_dump() for s in s_after]), encoding="utf-8")

    args = MockArgs(before=str(before), after=str(after))

    with pytest.raises(SystemExit):
        await run_analyze(args)

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    # Should have multiple findings
    assert len(data["findings"]) >= 2
    # Score should be accumulated significantly
    assert data["risk_score"] > 0
    # Classification should reflect the highest severity found (likely HIGH or MEDIUM depending on exact rules config)
    assert data["classification"] in ["HIGH", "MEDIUM"]

@pytest.mark.asyncio
async def test_mixed_input_json_sql(tmp_path, capsys):
    """Test mixed input format: JSON before + SQL after."""
    before = tmp_path / "before_mix.json"
    after = tmp_path / "after_mix.sql"

    s_before = [TableSchema(schema_name="S", table_name="T1", columns=[
        ColumnSchema(schema_name="S", table_name="T1", column_name="C1", data_type="INT", is_nullable=True, ordinal_position=1)
    ])]

    # SQL adds a column
    sql_ddl = "ALTER TABLE S.T1 ADD COLUMN C2 VARCHAR;"

    before.write_text(json.dumps([s.model_dump() for s in s_before]), encoding="utf-8")
    after.write_text(sql_ddl, encoding="utf-8")

    args = MockArgs(before=str(before), after=str(after))

    # Needs to handle SQL parsing, so we mock ddl parser just in case or rely on real one if simple
    # The real parser works for simple DDL, so let's try WITHOUT mocking first to test integration

    with pytest.raises(SystemExit):
        await run_analyze(args)

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    # Should detect the ADD COLUMN
    assert len(data["findings"]) > 0
    finding = next((f for f in data["findings"] if "added" in f["description"].lower()), None)

    assert finding is not None

