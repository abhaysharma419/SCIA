"""Tests for test_cli_main."""
import sys
import pytest
from unittest.mock import patch
from scia.cli.main import load_schema_file, main

def test_load_schema_file(fixtures_dir):
    """Test function."""
    schema = load_schema_file(str(fixtures_dir / "before.json"))
    assert len(schema) == 1
    assert schema[0].table_name == "ORDERS"

def test_load_schema_file_single_object(tmp_path):
    """Test function."""
    # Test loading a single object instead of a list
    f = tmp_path / "single.json"
    f.write_text('{"schema_name": "S", "table_name": "T", "columns": []}')
    schema = load_schema_file(str(f))
    assert len(schema) == 1
    assert schema[0].table_name == "T"

def test_main_analyze_success(fixtures_dir, capsys):
    """Test function."""
    test_args = ["scia", "analyze", "--before", str(fixtures_dir / "before.json"), "--after", str(fixtures_dir / "before.json")]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
        captured = capsys.readouterr()
        assert '"risk_score": 0' in captured.out

def test_main_diff_success(fixtures_dir, capsys):
    """Test function."""
    test_args = ["scia", "diff", "--before", str(fixtures_dir / "before.json"), "--after", str(fixtures_dir / "before.json")]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
        captured = capsys.readouterr()
        assert '"risk_score": 0' in captured.out

def test_main_analyze_fail_on_medium(fixtures_dir, capsys):
    """Test function."""
    test_args = ["scia", "analyze", "--before", str(fixtures_dir / "before.json"), "--after", str(fixtures_dir / "after.json"), "--fail-on", "MEDIUM"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1 # HIGH finding triggers fail-on MEDIUM

def test_main_analyze_markdown(fixtures_dir, capsys):
    """Test function."""
    test_args = ["scia", "analyze", "--before", str(fixtures_dir / "before.json"), "--after", str(fixtures_dir / "after.json"), "--format", "markdown"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
        captured = capsys.readouterr()
        assert "# SCIA Impact Report" in captured.out

def test_main_no_command(capsys):
    """Test function."""
    test_args = ["scia"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
