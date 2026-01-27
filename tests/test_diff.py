"""Tests for schema diffing functionality."""
from scia.core.diff import diff_schemas
from scia.models.schema import ColumnSchema, TableSchema

def test_no_op_diff():
    """Test that identical schemas produce no changes."""
    col = ColumnSchema(
        schema_name="S", table_name="T", column_name="C",
        data_type="INT", is_nullable=True, ordinal_position=1)
    table = TableSchema(schema_name="S", table_name="T", columns=[col])

    diff = diff_schemas([table], [table])
    assert len(diff.column_changes) == 0

def test_column_removal():
    """Test detection of removed columns."""
    col1 = ColumnSchema(
        schema_name="S", table_name="T", column_name="C1",
        data_type="INT", is_nullable=True, ordinal_position=1)
    col2 = ColumnSchema(
        schema_name="S", table_name="T", column_name="C2",
        data_type="INT", is_nullable=True, ordinal_position=2)

    table_before = TableSchema(
        schema_name="S", table_name="T", columns=[col1, col2])
    table_after = TableSchema(
        schema_name="S", table_name="T", columns=[col1])

    diff = diff_schemas([table_before], [table_after])
    assert len(diff.column_changes) == 1
    assert diff.column_changes[0].change_type == 'REMOVED'
    assert diff.column_changes[0].column_name == 'C2'

def test_column_type_change():
    """Test detection of column type changes."""
    col_before = ColumnSchema(
        schema_name="S", table_name="T", column_name="C",
        data_type="INT", is_nullable=True, ordinal_position=1)
    col_after = ColumnSchema(
        schema_name="S", table_name="T", column_name="C",
        data_type="STRING", is_nullable=True, ordinal_position=1)

    table_before = TableSchema(
        schema_name="S", table_name="T", columns=[col_before])
    table_after = TableSchema(
        schema_name="S", table_name="T", columns=[col_after])

    diff = diff_schemas([table_before], [table_after])
    assert len(diff.column_changes) == 1
    assert diff.column_changes[0].change_type == 'TYPE_CHANGED'
    assert diff.column_changes[0].before.data_type == 'INT'
    assert diff.column_changes[0].after.data_type == 'STRING'

def test_nullability_change():
    """Test detection of nullability constraint changes."""
    col_before = ColumnSchema(
        schema_name="S", table_name="T", column_name="C",
        data_type="INT", is_nullable=True, ordinal_position=1)
    col_after = ColumnSchema(
        schema_name="S", table_name="T", column_name="C",
        data_type="INT", is_nullable=False, ordinal_position=1)

    table_before = TableSchema(
        schema_name="S", table_name="T", columns=[col_before])
    table_after = TableSchema(
        schema_name="S", table_name="T", columns=[col_after])

    diff = diff_schemas([table_before], [table_after])
    assert len(diff.column_changes) == 1
    assert diff.column_changes[0].change_type == 'NULLABILITY_CHANGED'
    assert diff.column_changes[0].before.is_nullable is True
    assert diff.column_changes[0].after.is_nullable is False
