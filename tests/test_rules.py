from scia.core.rules import (
    rule_column_removed, rule_column_type_changed, rule_nullability_changed,
    rule_join_key_changed, rule_grain_change, rule_potential_breakage,
    rule_schema_removed, rule_schema_added, rule_table_removed, rule_table_added,
    apply_rules
)
from unittest.mock import MagicMock
from scia.core.diff import SchemaChange

def test_rule_schema_removed(schema_diff_factory):
    """Test schema removal detection."""
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="SCHEMA", schema_name="PUBLIC", change_type="REMOVED")
    ])
    findings = rule_schema_removed(diff)
    assert len(findings) == 1
    assert findings[0].finding_type == "SCHEMA_REMOVED"
    assert findings[0].severity == "HIGH"

def test_rule_table_removed(schema_diff_factory):
    """Test table removal detection."""
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="TABLE", schema_name="PUBLIC", table_name="USERS", change_type="REMOVED")
    ])
    findings = rule_table_removed(diff)
    assert len(findings) == 1
    assert findings[0].finding_type == "TABLE_REMOVED"
    assert findings[0].severity == "HIGH"

def test_rule_column_removed_applies(schema_diff_factory, column_factory):
    """Test function."""
    col = column_factory()
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C", change_type="REMOVED", before=col)
    ])
    findings = rule_column_removed(diff)
    assert len(findings) == 1
    assert findings[0].finding_type == "COLUMN_REMOVED"

def test_rule_column_removed_skips(schema_diff_factory, column_factory):
    """Test function."""
    col = column_factory()
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C", change_type="ADDED", after=col)
    ])
    findings = rule_column_removed(diff)
    assert len(findings) == 0

def test_rule_column_removed_aggregates(schema_diff_factory, column_factory):
    """Test function."""
    col1 = column_factory(column_name="C1")
    col2 = column_factory(column_name="C2")
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C1", change_type="REMOVED", before=col1),
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C2", change_type="REMOVED", before=col2)
    ])
    findings = rule_column_removed(diff)
    assert len(findings) == 2

def test_rule_column_type_changed_applies(schema_diff_factory, column_factory):
    """Test function."""
    col_b = column_factory(data_type="INT")
    col_a = column_factory(data_type="STRING")
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C", change_type="TYPE_CHANGED", before=col_b, after=col_a)
    ])
    findings = rule_column_type_changed(diff)
    assert len(findings) == 1
    assert findings[0].finding_type == "COLUMN_TYPE_CHANGED"

def test_rule_column_type_changed_skips(schema_diff_factory, column_factory):
    """Test function."""
    col = column_factory()
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C", change_type="ADDED", after=col)
    ])
    findings = rule_column_type_changed(diff)
    assert len(findings) == 0

def test_rule_column_type_changed_aggregates(schema_diff_factory, column_factory):
    """Test function."""
    col_b = column_factory(data_type="INT")
    col_a = column_factory(data_type="STRING")
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C1", change_type="TYPE_CHANGED", before=col_b, after=col_a),
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C2", change_type="TYPE_CHANGED", before=col_b, after=col_a)
    ])
    findings = rule_column_type_changed(diff)
    assert len(findings) == 2

def test_rule_nullability_changed_applies(schema_diff_factory, column_factory):
    """Test function."""
    col_b = column_factory(is_nullable=True)
    col_a = column_factory(is_nullable=False)
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C", change_type="NULLABILITY_CHANGED", before=col_b, after=col_a)
    ])
    findings = rule_nullability_changed(diff)
    assert len(findings) == 1
    assert findings[0].finding_type == "COLUMN_NULLABILITY_CHANGED"

def test_rule_nullability_changed_skips(schema_diff_factory, column_factory):
    """Test function."""
    # Changing from NOT NULL to NULL is usually not considered risky in this rule
    col_b = column_factory(is_nullable=False)
    col_a = column_factory(is_nullable=True)
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C", change_type="NULLABILITY_CHANGED", before=col_b, after=col_a)
    ])
    findings = rule_nullability_changed(diff)
    assert len(findings) == 0

def test_rule_nullability_changed_aggregates(schema_diff_factory, column_factory):
    """Test function."""
    col_b = column_factory(is_nullable=True)
    col_a = column_factory(is_nullable=False)
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C1", change_type="NULLABILITY_CHANGED", before=col_b, after=col_a),
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="C2", change_type="NULLABILITY_CHANGED", before=col_b, after=col_a)
    ])
    findings = rule_nullability_changed(diff)
    assert len(findings) == 2

def test_rule_join_key_changed_applies(schema_diff_factory, column_factory):
    """Test function."""
    col = column_factory(column_name="USER_ID")
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="USER_ID", change_type="REMOVED", before=col)
    ])
    # Mock SQLMetadata object
    mock_metadata = MagicMock()
    mock_metadata.join_keys = [("ORDER_ID", "USER_ID")]
    sql_signals = {"q": mock_metadata}
    
    findings = rule_join_key_changed(diff, sql_signals=sql_signals)
    assert len(findings) == 1
    assert findings[0].finding_type == "JOIN_KEY_CHANGED"
    assert findings[0].severity == "HIGH"

def test_rule_grain_change_applies(schema_diff_factory, column_factory):
    """Test function."""
    col = column_factory(column_name="REGION")
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="REGION", change_type="REMOVED", before=col)
    ])
    mock_metadata = MagicMock()
    mock_metadata.group_by_cols = {"REGION"}
    sql_signals = {"q": mock_metadata}
    
    findings = rule_grain_change(diff, sql_signals=sql_signals)
    assert len(findings) == 1
    assert findings[0].finding_type == "GRAIN_CHANGE"

def test_rule_potential_breakage_type_change(schema_diff_factory, column_factory):
    """Test function."""
    col_b = column_factory(column_name="REVENUE", data_type="DECIMAL(10,2)")
    col_a = column_factory(column_name="REVENUE", data_type="FLOAT")
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="REVENUE", 
                   change_type="TYPE_CHANGED", before=col_b, after=col_a)
    ])
    mock_metadata = MagicMock()
    mock_metadata.columns = {"REVENUE"}
    sql_signals = {"q": mock_metadata}
    
    findings = rule_potential_breakage(diff, sql_signals=sql_signals)
    assert len(findings) == 1
    assert findings[0].finding_type == "POTENTIAL_BREAKAGE"

def test_apply_rules_with_sql_signals(schema_diff_factory, column_factory):
    """Test function."""
    col = column_factory(column_name="USER_ID")
    diff = schema_diff_factory(changes=[
        SchemaChange(object_type="COLUMN", schema_name="S", table_name="T", column_name="USER_ID", change_type="REMOVED", before=col)
    ])
    mock_metadata = MagicMock()
    mock_metadata.join_keys = [("ORDER_ID", "USER_ID")]
    sql_signals = {"q": mock_metadata}
    
    findings = apply_rules(diff, sql_signals=sql_signals)
    types = [f.finding_type for f in findings]
    assert "COLUMN_REMOVED" in types
    assert "JOIN_KEY_CHANGED" in types
