import subprocess
import sys
import json
import pytest
from pathlib import Path

def run_cli(args):
    # Use the current python interpreter to run the scia module
    return subprocess.run(
        [sys.executable, "-m", "scia.cli.main"] + args,
        capture_output=True,
        text=True
    )


def test_cli_json_output(fixtures_dir):
    result = run_cli(["analyze", "--before", str(fixtures_dir / "before.json"), "--after", str(fixtures_dir / "after.json")])
    assert result.returncode == 1  # CUSTOMER_ID removed is HIGH risk
    data = json.loads(result.stdout)
    assert "risk_score" in data
    assert "classification" in data
    assert "findings" in data

def test_cli_markdown_output(fixtures_dir):
    result = run_cli(["analyze", "--before", str(fixtures_dir / "before.json"), "--after", str(fixtures_dir / "after.json"), "--format", "markdown"])
    assert result.returncode == 1
    assert "# SCIA Impact Report" in result.stdout
    assert "**Risk Score:**" in result.stdout

def test_cli_missing_file_error():
    result = run_cli(["analyze", "--before", "non_existent.json", "--after", "non_existent.json"])
    assert result.returncode == 1
    assert "Error: File not found" in result.stderr

def test_cli_invalid_json_error(tmp_path):
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("not json")
    result = run_cli(["analyze", "--before", str(invalid_json), "--after", str(invalid_json)])
    assert result.returncode == 1
    # Error will be caught by the json.load in load_schema_file

def test_cli_fail_on_behavior(fixtures_dir, tmp_path):
    # CUSTOMER_ID removed is HIGH risk (80)
    
    # --fail-on HIGH should fail on HIGH findings
    result = run_cli(["analyze", "--before", str(fixtures_dir / "before.json"), "--after", str(fixtures_dir / "after.json"), "--fail-on", "HIGH"])
    assert result.returncode == 1
    
    # Create a MEDIUM risk change (type change)
    medium_before = tmp_path / "med_before.json"
    medium_after = tmp_path / "med_after.json"
    
    schema = [
        {
            "schema_name": "S", "table_name": "T",
            "columns": [{"schema_name": "S", "table_name": "T", "column_name": "C", "data_type": "INT", "is_nullable": True, "ordinal_position": 1}]
        }
    ]
    schema_after = [
        {
            "schema_name": "S", "table_name": "T",
            "columns": [{"schema_name": "S", "table_name": "T", "column_name": "C", "data_type": "STRING", "is_nullable": True, "ordinal_position": 1}]
        }
    ]
    medium_before.write_text(json.dumps(schema))
    medium_after.write_text(json.dumps(schema_after))
    
    # --fail-on HIGH should PASS on MEDIUM findings
    result = run_cli(["analyze", "--before", str(medium_before), "--after", str(medium_after), "--fail-on", "HIGH"])
    assert result.returncode == 0
    
    # --fail-on MEDIUM should FAIL on MEDIUM findings
    result = run_cli(["analyze", "--before", str(medium_before), "--after", str(medium_after), "--fail-on", "MEDIUM"])
    assert result.returncode == 1

def test_cli_format_flag_validation(fixtures_dir):
    result = run_cli(["analyze", "--before", str(fixtures_dir / "before.json"), "--after", str(fixtures_dir / "after.json"), "--format", "xml"])
    assert result.returncode != 0
    assert "argument --format: invalid choice" in result.stderr

def test_cli_empty_schema(tmp_path):
    empty_json = tmp_path / "empty.json"
    empty_json.write_text("[]")
    result = run_cli(["analyze", "--before", str(empty_json), "--after", str(empty_json)])
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["risk_score"] == 0
    assert data["classification"] == "LOW"

def test_cli_multiple_findings(fixtures_dir):
    # Using before.json and after.json should have at least one finding (the removal)
    result = run_cli(["analyze", "--before", str(fixtures_dir / "before.json"), "--after", str(fixtures_dir / "after.json")])
    data = json.loads(result.stdout)
    assert len(data["findings"]) >= 1
