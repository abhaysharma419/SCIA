"""Integration tests for the SCIA CLI."""
import subprocess
import sys
import json

def run_cli(args):
    """Helper to run the SCIA CLI as a subprocess."""
    # Use the current python interpreter to run the scia module
    return subprocess.run(
        [sys.executable, "-m", "scia.cli.main"] + args,
        capture_output=True,
        text=True,
        check=False
    )


def test_cli_json_output(fixtures_dir):
    """Test that CLI produces valid JSON output."""
    before = str(fixtures_dir / "before.json")
    after = str(fixtures_dir / "after.json")
    result = run_cli(["analyze", "--before", before, "--after", after])
    assert result.returncode == 1  # CUSTOMER_ID removed is HIGH risk
    data = json.loads(result.stdout)
    assert "risk_score" in data
    assert "classification" in data
    assert "findings" in data

def test_cli_markdown_output(fixtures_dir):
    """Test that CLI produces markdown output."""
    before = str(fixtures_dir / "before.json")
    after = str(fixtures_dir / "after.json")
    result = run_cli(["analyze", "--before", before, "--after", after, "--format", "markdown"])
    assert result.returncode == 1
    assert "# SCIA Impact Report" in result.stdout
    assert "**Risk Score:**" in result.stdout

def test_cli_missing_file_error():
    """Test error handling when input files are missing."""
    result = run_cli(["analyze", "--before", "non_existent.json", "--after", "non_existent.json"])
    assert result.returncode == 1
    assert "not found" in result.stderr.lower()

def test_cli_invalid_json_error(tmp_path):
    """Test error handling for invalid JSON input files."""
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("not json", encoding="utf-8")
    result = run_cli(["analyze", "--before", str(invalid_json), "--after", str(invalid_json)])
    assert result.returncode == 1
    # Error will be caught by the json.load in load_schema_file

def test_cli_fail_on_behavior(fixtures_dir, tmp_path):
    """Test the --fail-on flag behavior for different risk levels."""
    # CUSTOMER_ID removed is HIGH risk (80)

    # --fail-on HIGH should fail on HIGH findings
    before = str(fixtures_dir / "before.json")
    after = str(fixtures_dir / "after.json")
    result = run_cli(["analyze", "--before", before, "--after", after, "--fail-on", "HIGH"])
    assert result.returncode == 1

    # Create a MEDIUM risk change (type change)
    medium_before = tmp_path / "med_before.json"
    medium_after = tmp_path / "med_after.json"

    schema = [
        {
            "schema_name": "S", "table_name": "T",
            "columns": [{
                "schema_name": "S", "table_name": "T", "column_name": "C",
                "data_type": "INT", "is_nullable": True, "ordinal_position": 1
            }]
        }
    ]
    schema_after = [
        {
            "schema_name": "S", "table_name": "T",
            "columns": [{
                "schema_name": "S", "table_name": "T", "column_name": "C",
                "data_type": "STRING", "is_nullable": True, "ordinal_position": 1
            }]
        }
    ]
    medium_before.write_text(json.dumps(schema), encoding="utf-8")
    medium_after.write_text(json.dumps(schema_after), encoding="utf-8")

    # --fail-on HIGH should PASS on MEDIUM findings
    # Note: As of v0.2, type changes are HIGH risk (90) due to 
    # combined rule_column_type_changed (40) + rule_potential_breakage (50).
    # To get a MEDIUM risk, we can use a nullability change.
    
    null_before = tmp_path / "null_before.json"
    null_after = tmp_path / "null_after.json"
    
    null_schema = [
        {
            "schema_name": "S", "table_name": "T",
            "columns": [{
                "schema_name": "S", "table_name": "T", "column_name": "C",
                "data_type": "INT", "is_nullable": True, "ordinal_position": 1
            }]
        }
    ]
    null_schema_after = [
        {
            "schema_name": "S", "table_name": "T",
            "columns": [{
                "schema_name": "S", "table_name": "T", "column_name": "C",
                "data_type": "INT", "is_nullable": False, "ordinal_position": 1
            }]
        }
    ]
    null_before.write_text(json.dumps(null_schema), encoding="utf-8")
    null_after.write_text(json.dumps(null_schema_after), encoding="utf-8")

    result = run_cli([
        "analyze", "--before", str(null_before), "--after", str(null_after),
        "--fail-on", "HIGH"
    ])
    # Nullability change is 50 risk (MEDIUM)
    assert result.returncode == 0

    # --fail-on MEDIUM should FAIL on MEDIUM findings
    result = run_cli([
        "analyze", "--before", str(null_before), "--after", str(null_after),
        "--fail-on", "MEDIUM"
    ])
    assert result.returncode == 1

def test_cli_format_flag_validation(fixtures_dir):
    """Test validation of the --format flag."""
    before = str(fixtures_dir / "before.json")
    after = str(fixtures_dir / "after.json")
    result = run_cli(["analyze", "--before", before, "--after", after, "--format", "xml"])
    assert result.returncode != 0
    assert "argument --format: invalid choice" in result.stderr

def test_cli_empty_schema(tmp_path):
    """Test behavior with empty schema inputs."""
    empty_json = tmp_path / "empty.json"
    empty_json.write_text("[]", encoding="utf-8")
    result = run_cli(["analyze", "--before", str(empty_json), "--after", str(empty_json)])
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["risk_score"] == 0
    assert data["classification"] == "LOW"

def test_cli_multiple_findings(fixtures_dir):
    """Test that multiple findings are correctly reported."""
    # Using before.json and after.json should have at least one finding (the removal)
    before = str(fixtures_dir / "before.json")
    after = str(fixtures_dir / "after.json")
    result = run_cli(["analyze", "--before", before, "--after", after])
    data = json.loads(result.stdout)
    assert len(data["findings"]) >= 1
