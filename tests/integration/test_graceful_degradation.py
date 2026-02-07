"""Graceful degradation tests for SCIA CLI."""
import json
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
async def test_warehouse_connection_failure_degradation(tmp_path, capsys):
    """Test that warehouse connection failure doesn't crash the analysis."""
    # Create dummy JSON files
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text("[]", encoding="utf-8")
    after.write_text("[]", encoding="utf-8")

    args = MockArgs(
        before=str(before),
        after=str(after),
        warehouse="snowflake"
    )

    with patch("scia.cli.main.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_adapter.connect.side_effect = Exception("Connection timeout")
        mock_get_adapter.return_value = mock_adapter

        # We expect it to NOT sys.exit(1) but continue
        # However, run_analyze calls sys.exit(0) at the end, which raises SystemExit
        with pytest.raises(SystemExit) as excinfo:
            await run_analyze(args)

        # If it failed gracefully, it should exit with 0 (no findings in empty schema)
        assert excinfo.value.code == 0

        captured = capsys.readouterr()
        # Should have warned about connection failure
        assert "Warning" in captured.err or "Warning" in captured.out
        # Output should still be valid JSON
        data = json.loads(captured.out)
        assert "findings" in data

@pytest.mark.asyncio
async def test_sql_parsing_failure_degradation(tmp_path, capsys):
    """Test that SQL parsing failure doesn't crash the analysis."""
    before = tmp_path / "before.json"
    after = tmp_path / "after.sql"
    before.write_text("[]", encoding="utf-8")
    after.write_text("INVALID SQL;", encoding="utf-8")

    args = MockArgs(
        before=str(before),
        after=str(after)
    )

    with patch("scia.cli.main.parse_ddl_to_schema") as mock_parse:
        mock_parse.side_effect = Exception("Parser error")

        with pytest.raises(SystemExit) as excinfo:
            await run_analyze(args)

        assert excinfo.value.code == 0 # or 1 if it decided to fail, but roadmap says "continue"

        captured = capsys.readouterr()
        assert "findings" in json.loads(captured.out)

@pytest.mark.asyncio
async def test_metadata_missing_degradation(tmp_path, capsys):
    """Test that missing optional metadata continues gracefully."""
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text("[]", encoding="utf-8")
    after.write_text("[]", encoding="utf-8")

    args = MockArgs(
        before=str(before),
        after=str(after),
        warehouse="snowflake"
    )

    with patch("scia.cli.main.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_adapter.fetch_views.side_effect = Exception("Views unavailable")
        mock_adapter.fetch_foreign_keys.side_effect = Exception("FKs unavailable")
        mock_get_adapter.return_value = mock_adapter

        with pytest.raises(SystemExit) as excinfo:
            await run_analyze(args)

        assert excinfo.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        data = json.loads(captured.out)
        assert "findings" in data

@pytest.mark.asyncio
async def test_foreign_keys_unavailable_only(tmp_path, caplog):  # pylint: disable=unused-argument
    """Test that missing FKs doesn't crash upstream analysis."""
    # Create simple table that would have upstream deps normally
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"

    # Introduce a change to trigger impact analysis
    schema_before = [TableSchema(schema_name="S", table_name="T1", columns=[
        ColumnSchema(schema_name="S", table_name="T1", column_name="C1", data_type="INT", is_nullable=True, ordinal_position=1)
    ])]
    schema_after = [TableSchema(schema_name="S", table_name="T1", columns=[
        ColumnSchema(schema_name="S", table_name="T1", column_name="C1", data_type="INT", is_nullable=True, ordinal_position=1),
        ColumnSchema(schema_name="S", table_name="T1", column_name="C2", data_type="INT", is_nullable=True, ordinal_position=2)
    ])]

    before.write_text(json.dumps([s.model_dump() for s in schema_before]), encoding="utf-8")
    after.write_text(json.dumps([s.model_dump() for s in schema_after]), encoding="utf-8")

    args = MockArgs(
        before=str(before),
        after=str(after),
        warehouse="snowflake"
    )

    with patch("scia.cli.main.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_adapter.fetch_views.return_value = {} # Views work
        mock_adapter.fetch_foreign_keys.side_effect = Exception("FKs unavailable") # FKs fail
        mock_get_adapter.return_value = mock_adapter

        with pytest.raises(SystemExit) as excinfo:
            await run_analyze(args)

        assert excinfo.value.code == 0
        # Should warning about FK failure in logs
        assert "Failed to fetch foreign keys" in caplog.text

@pytest.mark.asyncio
async def test_max_depth_limits(tmp_path, capsys):  # pylint: disable=unused-argument
    """Test that max_depth limits (1 and 10) work without error."""
    # We just want to ensure it runs without error validation complaints
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text("[]", encoding="utf-8")
    after.write_text("[]", encoding="utf-8")

    # Test depth 1
    args1 = MockArgs(before=str(before), after=str(after), warehouse="snowflake", dependency_depth=1)

    with patch("scia.cli.main.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        with pytest.raises(SystemExit) as excinfo:
            await run_analyze(args1)
        assert excinfo.value.code == 0

    # Test depth 10
    args10 = MockArgs(before=str(before), after=str(after), warehouse="snowflake", dependency_depth=10)

    with patch("scia.cli.main.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        with pytest.raises(SystemExit) as excinfo:
            await run_analyze(args10)
        assert excinfo.value.code == 0

