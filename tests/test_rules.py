from scia.core.rules import (
    rule_column_removed, rule_column_type_changed, rule_nullability_changed
)
from scia.core.diff import ColumnDiff

def test_rule_column_removed_applies(schema_diff_factory, column_factory):
    col = column_factory()
    diff = schema_diff_factory(column_changes=[
        ColumnDiff(schema_name="S", table_name="T", column_name="C", change_type="REMOVED", before=col)
    ])
    findings = rule_column_removed(diff)
    assert len(findings) == 1
    assert findings[0].finding_type == "COLUMN_REMOVED"

def test_rule_column_removed_skips(schema_diff_factory, column_factory):
    col = column_factory()
    diff = schema_diff_factory(column_changes=[
        ColumnDiff(schema_name="S", table_name="T", column_name="C", change_type="ADDED", after=col)
    ])
    findings = rule_column_removed(diff)
    assert len(findings) == 0

def test_rule_column_removed_aggregates(schema_diff_factory, column_factory):
    col1 = column_factory(column_name="C1")
    col2 = column_factory(column_name="C2")
    diff = schema_diff_factory(column_changes=[
        ColumnDiff(schema_name="S", table_name="T", column_name="C1", change_type="REMOVED", before=col1),
        ColumnDiff(schema_name="S", table_name="T", column_name="C2", change_type="REMOVED", before=col2)
    ])
    findings = rule_column_removed(diff)
    assert len(findings) == 2

def test_rule_column_type_changed_applies(schema_diff_factory, column_factory):
    col_b = column_factory(data_type="INT")
    col_a = column_factory(data_type="STRING")
    diff = schema_diff_factory(column_changes=[
        ColumnDiff(schema_name="S", table_name="T", column_name="C", change_type="TYPE_CHANGED", before=col_b, after=col_a)
    ])
    findings = rule_column_type_changed(diff)
    assert len(findings) == 1
    assert findings[0].finding_type == "COLUMN_TYPE_CHANGED"

def test_rule_column_type_changed_skips(schema_diff_factory, column_factory):
    col = column_factory()
    diff = schema_diff_factory(column_changes=[
        ColumnDiff(schema_name="S", table_name="T", column_name="C", change_type="ADDED", after=col)
    ])
    findings = rule_column_type_changed(diff)
    assert len(findings) == 0

def test_rule_column_type_changed_aggregates(schema_diff_factory, column_factory):
    col_b = column_factory(data_type="INT")
    col_a = column_factory(data_type="STRING")
    diff = schema_diff_factory(column_changes=[
        ColumnDiff(schema_name="S", table_name="T", column_name="C1", change_type="TYPE_CHANGED", before=col_b, after=col_a),
        ColumnDiff(schema_name="S", table_name="T", column_name="C2", change_type="TYPE_CHANGED", before=col_b, after=col_a)
    ])
    findings = rule_column_type_changed(diff)
    assert len(findings) == 2

def test_rule_nullability_changed_applies(schema_diff_factory, column_factory):
    col_b = column_factory(is_nullable=True)
    col_a = column_factory(is_nullable=False)
    diff = schema_diff_factory(column_changes=[
        ColumnDiff(schema_name="S", table_name="T", column_name="C", change_type="NULLABILITY_CHANGED", before=col_b, after=col_a)
    ])
    findings = rule_nullability_changed(diff)
    assert len(findings) == 1
    assert findings[0].finding_type == "COLUMN_NULLABILITY_CHANGED"

def test_rule_nullability_changed_skips(schema_diff_factory, column_factory):
    # Changing from NOT NULL to NULL is usually not considered risky in this rule
    col_b = column_factory(is_nullable=False)
    col_a = column_factory(is_nullable=True)
    diff = schema_diff_factory(column_changes=[
        ColumnDiff(schema_name="S", table_name="T", column_name="C", change_type="NULLABILITY_CHANGED", before=col_b, after=col_a)
    ])
    findings = rule_nullability_changed(diff)
    assert len(findings) == 0

def test_rule_nullability_changed_aggregates(schema_diff_factory, column_factory):
    col_b = column_factory(is_nullable=True)
    col_a = column_factory(is_nullable=False)
    diff = schema_diff_factory(column_changes=[
        ColumnDiff(schema_name="S", table_name="T", column_name="C1", change_type="NULLABILITY_CHANGED", before=col_b, after=col_a),
        ColumnDiff(schema_name="S", table_name="T", column_name="C2", change_type="NULLABILITY_CHANGED", before=col_b, after=col_a)
    ])
    findings = rule_nullability_changed(diff)
    assert len(findings) == 2
