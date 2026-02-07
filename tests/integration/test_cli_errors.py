"""CLI error handling tests for SCIA."""
import subprocess
import sys

def run_cli(args):
    """Helper to run the SCIA CLI as a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "scia.cli.main"] + args,
        capture_output=True,
        text=True,
        check=False
    )

def test_missing_warehouse_for_db_mode():
    """Test error message when --warehouse is missing for DB mode."""
    # SCHEMA.TABLE format triggers DB mode
    result = run_cli(["analyze", "--before", "PROD.T1", "--after", "DEV.T1"])
    assert result.returncode == 1
    assert "requires --warehouse parameter" in result.stderr

def test_invalid_warehouse_choice():
    """Test error message for invalid warehouse choice."""
    result = run_cli([
        "analyze", "--before", "b.json", "--after", "a.json", "--warehouse", "oracle"
    ])
    assert result.returncode != 0
    assert "invalid choice: 'oracle'" in result.stderr

def test_invalid_dependency_depth():
    """Test that invalid dependency depth is handled (argparse handles int)."""
    # Literal string 'abc' should fail argparse validation
    result = run_cli([
        "analyze", "--before", "b.json", "--after", "a.json",
        "--dependency-depth", "abc"
    ])
    assert result.returncode != 0
    assert "invalid int value" in result.stderr

def test_malformed_config_file(tmp_path):
    """Test handling of malformed connection config file."""
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text("invalid: [yaml", encoding="utf-8")

    # We need to trigger a connection to see the config loading
    # But since we're using real code here, and SnowflakeAdapter.connect
    # might fail differently, let's just check if it warns/errors.
    result = run_cli([
        "analyze",
        "--before", "S.T1",
        "--after", "S.T2",
        "--warehouse", "snowflake",
        "--conn-file", str(bad_config)
    ])
    assert result.returncode == 1 # Error: Failed to connect... (due to malformed yaml)
    assert "Error" in result.stderr or "Warning" in result.stderr

def test_missing_connection_credentials(tmp_path):
    """Test that missing credentials result in a helpful error (or warning)."""
    # Create a config file with missing fields (empty dict)
    empty_config = tmp_path / "empty.yaml"
    empty_config.write_text("{}", encoding="utf-8")

    # Run CLI in DB mode (requires valid connection)
    result = run_cli([
        "analyze",
        "--before", "S.T1",
        "--after", "S.T2",
        "--warehouse", "snowflake",
        "--conn-file", str(empty_config)
    ])

    # Should fail because DB mode requires working adapter
    assert result.returncode == 1

    # Should see connection failure warning
    # exact message depends on snowflake connector but usually contains "account" or similar
    # And our code prints "Warning: Failed to connect..."
    assert "Warning: Failed to connect" in result.stderr

    # And specifically, it fails because default params are empty strings which snowflake rejects
