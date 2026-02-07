"""Graceful degradation tests for SCIA CLI."""
import json
from unittest.mock import MagicMock, patch
import pytest
from scia.cli.main import run_analyze

class MockArgs:
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
        assert "findings" in data
