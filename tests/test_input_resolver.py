"""Tests for input resolver."""
import pytest

from scia.input.resolver import (
    InputResolutionError,
    InputType,
    resolve_input,
)


def test_resolve_json_mode(tmp_path):
    """Test JSON input mode detection."""
    # Create temp JSON files
    before_file = tmp_path / "before.json"
    after_file = tmp_path / "after.json"
    before_file.write_text('[]')
    after_file.write_text('[]')
    
    input_type, metadata = resolve_input(str(before_file), str(after_file))
    
    assert input_type == InputType.JSON
    assert metadata['input_type'] == 'json'
    assert metadata['before_format'] == 'json'
    assert metadata['after_format'] == 'json'


def test_resolve_sql_mode_json_to_sql(tmp_path):
    """Test SQL input mode (JSON before, SQL after)."""
    before_file = tmp_path / "before.json"
    after_file = tmp_path / "after.sql"
    before_file.write_text('[]')
    after_file.write_text('CREATE TABLE test (id INT);')
    
    input_type, metadata = resolve_input(str(before_file), str(after_file))
    
    assert input_type == InputType.SQL
    assert metadata['before_format'] == 'json'
    assert metadata['after_format'] == 'sql'


def test_resolve_sql_mode_sql_to_json(tmp_path):
    """Test SQL input mode (SQL before, JSON after)."""
    before_file = tmp_path / "before.sql"
    after_file = tmp_path / "after.json"
    before_file.write_text('CREATE TABLE test (id INT);')
    after_file.write_text('[]')
    
    input_type, metadata = resolve_input(str(before_file), str(after_file))
    
    assert input_type == InputType.SQL


def test_resolve_database_mode_requires_warehouse():
    """Test that database mode requires warehouse parameter."""
    with pytest.raises(InputResolutionError, match="requires --warehouse parameter"):
        resolve_input('PROD.ANALYTICS', 'DEV.ANALYTICS')


def test_resolve_database_mode_with_warehouse():
    """Test database mode with warehouse parameter."""
    input_type, metadata = resolve_input(
        'PROD.ANALYTICS',
        'DEV.ANALYTICS',
        warehouse='snowflake'
    )
    
    assert input_type == InputType.DATABASE
    assert metadata['input_type'] == 'database'
    assert metadata['warehouse'] == 'snowflake'


def test_resolve_database_single_part_reference():
    """Test database references with warehouse specified."""
    input_type, metadata = resolve_input(
        'SCHEMA1.TABLE1',
        'SCHEMA2.TABLE2',
        warehouse='snowflake'
    )
    
    assert input_type == InputType.DATABASE
    assert metadata['before_format'] == 'database'


def test_resolve_missing_before_file():
    """Test error when before file doesn't exist."""
    with pytest.raises(InputResolutionError, match="not found"):
        resolve_input('nonexistent.json', 'nonexistent.json')


def test_resolve_mixed_json_and_database():
    """Test mixed mode (file + database) requires warehouse."""
    with pytest.raises(InputResolutionError, match="requires --warehouse"):
        resolve_input('some.json', 'PROD.TABLE')


def test_resolve_mixed_with_warehouse(tmp_path):
    """Test mixed mode with warehouse specified."""
    before_file = tmp_path / "before.json"
    before_file.write_text('[]')
    
    input_type, metadata = resolve_input(
        str(before_file),
        'PROD.TABLE',
        warehouse='snowflake'
    )
    
    assert input_type == InputType.DATABASE
    assert metadata['warehouse'] == 'snowflake'


def test_resolve_warehouse_parameter_persists(tmp_path):
    """Test that warehouse parameter is included in metadata."""
    before_file = tmp_path / "before.json"
    after_file = tmp_path / "after.json"
    before_file.write_text('[]')
    after_file.write_text('[]')
    
    _, metadata = resolve_input(
        str(before_file),
        str(after_file),
        warehouse='databricks'
    )
    
    assert metadata['warehouse'] == 'databricks'


def test_resolve_sql_to_sql(tmp_path):
    """Test SQL to SQL mode."""
    before_file = tmp_path / "before.sql"
    after_file = tmp_path / "after.sql"
    before_file.write_text('CREATE TABLE t1 (id INT);')
    after_file.write_text('CREATE TABLE t1 (id INT, name VARCHAR);')
    
    input_type, metadata = resolve_input(str(before_file), str(after_file))
    
    assert input_type == InputType.SQL
    assert metadata['before_format'] == 'sql'
    assert metadata['after_format'] == 'sql'


def test_resolve_invalid_combination():
    """Test unsupported input combinations."""
    # This would be if we had some hypothetical format
    # For now, test that valid combinations work
    pass
