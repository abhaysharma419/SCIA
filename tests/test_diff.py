"""Tests for schema diffing functionality."""
from scia.core.diff import diff_schemas

def test_no_op_diff(table_factory):
    """Test that identical schemas produce no changes."""
    table = table_factory()
    diff = diff_schemas([table], [table])
    assert len(diff.column_changes) == 0

def test_column_addition(table_factory, column_factory):
    """Test detection of added columns."""
    col1 = column_factory(column_name="C1")
    col2 = column_factory(column_name="C2")

    table_before = table_factory(columns=[col1])
    table_after = table_factory(columns=[col1, col2])

    diff = diff_schemas([table_before], [table_after])
    assert len(diff.column_changes) == 1
    assert diff.column_changes[0].change_type == 'ADDED'
    assert diff.column_changes[0].column_name == 'C2'

def test_column_removal(table_factory, column_factory):
    """Test detection of removed columns."""
    col1 = column_factory(column_name="C1")
    col2 = column_factory(column_name="C2")

    table_before = table_factory(columns=[col1, col2])
    table_after = table_factory(columns=[col1])

    diff = diff_schemas([table_before], [table_after])
    assert len(diff.column_changes) == 1
    assert diff.column_changes[0].change_type == 'REMOVED'
    assert diff.column_changes[0].column_name == 'C2'

def test_column_type_change(table_factory, column_factory):
    """Test detection of column type changes."""
    col_before = column_factory(data_type="INT")
    col_after = column_factory(data_type="STRING")

    table_before = table_factory(columns=[col_before])
    table_after = table_factory(columns=[col_after])

    diff = diff_schemas([table_before], [table_after])
    assert len(diff.column_changes) == 1
    assert diff.column_changes[0].change_type == 'TYPE_CHANGED'
    assert diff.column_changes[0].before.data_type == 'INT'
    assert diff.column_changes[0].after.data_type == 'STRING'

def test_nullability_change(table_factory, column_factory):
    """Test detection of nullability constraint changes."""
    col_before = column_factory(is_nullable=True)
    col_after = column_factory(is_nullable=False)

    table_before = table_factory(columns=[col_before])
    table_after = table_factory(columns=[col_after])

    diff = diff_schemas([table_before], [table_after])
    assert len(diff.column_changes) == 1
    assert diff.column_changes[0].change_type == 'NULLABILITY_CHANGED'
    assert diff.column_changes[0].before.is_nullable is True
    assert diff.column_changes[0].after.is_nullable is False

def test_table_addition(table_factory):
    """Test detection of added tables."""
    table = table_factory(table_name="NEW_TABLE")

    diff = diff_schemas([], [table])
    assert len(diff.column_changes) == 1
    assert diff.column_changes[0].table_name == "NEW_TABLE"
    assert diff.column_changes[0].change_type == 'ADDED'

def test_table_removal(table_factory):
    """Test detection of removed tables."""
    table = table_factory(table_name="OLD_TABLE")

    diff = diff_schemas([table], [])
    assert len(diff.column_changes) == 1
    assert diff.column_changes[0].table_name == "OLD_TABLE"
    assert diff.column_changes[0].change_type == 'REMOVED'

def test_multiple_changes(table_factory, column_factory):
    """Test detection of multiple changes across tables."""
    col1_before = column_factory(table_name="T1", column_name="C1", data_type="INT")
    col1_after = column_factory(table_name="T1", column_name="C1", data_type="STRING")
    col2 = column_factory(table_name="T1", column_name="C2")

    table1_before = table_factory(table_name="T1", columns=[col1_before])
    table1_after = table_factory(table_name="T1", columns=[col1_after, col2])

    table2_before = table_factory(table_name="T2")
    # table2 removed in after

    diff = diff_schemas([table1_before, table2_before], [table1_after])

    # Changes:
    # 1. T1.C1 type change
    # 2. T1.C2 added
    # 3. T2.TEST_COL removed (because T2 was removed)
    assert len(diff.column_changes) == 3
    change_types = [c.change_type for c in diff.column_changes]
    assert 'TYPE_CHANGED' in change_types
    assert 'ADDED' in change_types
    assert 'REMOVED' in change_types
