"""Backward compatibility tests for SCIA CLI."""
import subprocess
import sys
import json
import pytest

def run_cli(args):
    """Helper to run the SCIA CLI as a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "scia.cli.main"] + args,
        capture_output=True,
        text=True,
        check=False
    )

def test_legacy_diff_command(fixtures_dir):
    """Test that the legacy 'diff' command still works."""
    before = str(fixtures_dir / "before.json")
    after = str(fixtures_dir / "after.json")
    
    # Run 'diff' instead of 'analyze'
    result = run_cli(["diff", "--before", before, "--after", after])
    
    # Should work identically to 'analyze' for JSON files
    assert result.returncode == 1 # CUSTOMER_ID removed is HIGH
    data = json.loads(result.stdout)
    assert data["classification"] == "HIGH"
    assert len(data["findings"]) > 0

def test_analyze_json_no_extra_flags(fixtures_dir):
    """Test analyze command with basic JSON inputs, no v0.2 flags."""
    before = str(fixtures_dir / "before.json")
    after = str(fixtures_dir / "after.json")
    
    result = run_cli(["analyze", "--before", before, "--after", after])
    
    assert result.returncode == 1
    data = json.loads(result.stdout)
    # v0.2 should not add 'impact_detail' if not requested/possible
    for finding in data["findings"]:
        assert "impact_detail" not in finding or finding["impact_detail"] is None

def test_fail_on_backward_compat(fixtures_dir):
    """Test that --fail-on still behaves as expected for JSON inputs."""
    before = str(fixtures_dir / "before.json")
    after = str(fixtures_dir / "after.json")
    
    # HIGH findings should fail when --fail-on HIGH
    result = run_cli(["analyze", "--before", before, "--after", after, "--fail-on", "HIGH"])
    assert result.returncode == 1
    
    # HIGH findings should ALSO fail when --fail-on MEDIUM
    result = run_cli(["analyze", "--before", before, "--after", after, "--fail-on", "MEDIUM"])
    assert result.returncode == 1

def test_ignored_v02_flags_in_json_mode(fixtures_dir):
    """Test that v0.2 flags don't break JSON mode even if provided."""
    before = str(fixtures_dir / "before.json")
    after = str(fixtures_dir / "after.json")
    
    # These flags shouldn't cause errors in JSON mode, though they might be ignored
    result = run_cli([
        "analyze", 
        "--before", before, 
        "--after", after, 
        "--dependency-depth", "5",
        "--include-upstream",
        "--no-downstream"
    ])
    
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert "findings" in data
