"""Detection rules for schema changes."""
from typing import Any, Dict, List, Optional

from scia.core.diff import SchemaDiff
from scia.models.finding import Finding, FindingType, Severity

def rule_schema_removed(diff: SchemaDiff) -> List[Finding]:
    """Detect removed schemas."""
    findings = []
    for change in diff.changes:
        if change.object_type == 'SCHEMA' and change.change_type == 'REMOVED':
            findings.append(Finding(
                finding_type=FindingType.SCHEMA_REMOVED,
                severity=Severity.HIGH,
                base_risk=100,
                evidence={"schema": change.schema_name},
                description=f"Schema '{change.schema_name}' was removed."
            ))
    return findings

def rule_schema_added(diff: SchemaDiff) -> List[Finding]:
    """Detect added schemas."""
    findings = []
    for change in diff.changes:
        if change.object_type == 'SCHEMA' and change.change_type == 'ADDED':
            findings.append(Finding(
                finding_type=FindingType.SCHEMA_ADDED,
                severity=Severity.LOW,
                base_risk=0,
                evidence={"schema": change.schema_name},
                description=f"New schema '{change.schema_name}' was added."
            ))
    return findings

def rule_table_removed(diff: SchemaDiff) -> List[Finding]:
    """Detect removed tables."""
    findings = []
    for change in diff.changes:
        if change.object_type == 'TABLE' and change.change_type == 'REMOVED':
            findings.append(Finding(
                finding_type=FindingType.TABLE_REMOVED,
                severity=Severity.HIGH,
                base_risk=90,
                evidence={"schema": change.schema_name, "table": change.table_name},
                description=f"Table '{change.table_name}' was removed from "
                            f"schema '{change.schema_name}'."
            ))
    return findings

def rule_table_added(diff: SchemaDiff) -> List[Finding]:
    """Detect added tables."""
    findings = []
    for change in diff.changes:
        if change.object_type == 'TABLE' and change.change_type == 'ADDED':
            findings.append(Finding(
                finding_type=FindingType.TABLE_ADDED,
                severity=Severity.LOW,
                base_risk=0,
                evidence={"schema": change.schema_name, "table": change.table_name},
                description=f"New table '{change.table_name}' was added to "
                            f"schema '{change.schema_name}'."
            ))
    return findings

def rule_column_removed(diff: SchemaDiff) -> List[Finding]:
    """Detect removed columns."""
    findings = []
    for change in diff.changes:
        if change.object_type == 'COLUMN' and change.change_type == 'REMOVED':
            findings.append(Finding(
                finding_type=FindingType.COLUMN_REMOVED,
                severity=Severity.HIGH,
                base_risk=80,
                evidence={"schema": change.schema_name, "table": change.table_name, "column": change.column_name},
                description=(
                    f"Column '{change.column_name}' removed from table "
                    f"'{change.table_name}'."
                )
            ))
    return findings

def rule_column_added(diff: SchemaDiff) -> List[Finding]:
    """Detect added columns."""
    findings = []
    for change in diff.changes:
        if change.object_type == 'COLUMN' and change.change_type == 'ADDED':
            findings.append(Finding(
                finding_type=FindingType.COLUMN_ADDED,
                severity=Severity.LOW,
                base_risk=0,
                evidence={"schema": change.schema_name, "table": change.table_name, "column": change.column_name},
                description=(
                    f"New column '{change.column_name}' added to table "
                    f"'{change.table_name}'."
                )
            ))
    return findings

def rule_column_type_changed(diff: SchemaDiff,
                             sql_signals: Optional[Dict[str, Any]] = None) -> List[Finding]:
    """Detect column type changes."""
    findings = []

    referenced_columns = set()
    if sql_signals:
        for metadata in sql_signals.values():
            if hasattr(metadata, 'columns'):
                for col in metadata.columns:
                    referenced_columns.add(col.upper())

    for change in diff.changes:
        if change.object_type == 'COLUMN' and change.change_type == 'TYPE_CHANGED':
            # Base risk for type change
            risk = 40
            severity = Severity.MEDIUM

            # If we know the column is used in SQL, increase risk
            if sql_signals and change.column_name.upper() in referenced_columns:
                risk = 50
                severity = Severity.MEDIUM # Still medium, but higher score

            findings.append(Finding(
                finding_type=FindingType.COLUMN_TYPE_CHANGED,
                severity=severity,
                base_risk=risk,
                evidence={
                    "schema": change.schema_name,
                    "table": change.table_name,
                    "column": change.column_name,
                    "before": change.before.data_type,
                    "after": change.after.data_type
                },
                description=(
                    f"Column '{change.column_name}' type changed from "
                    f"{change.before.data_type} to {change.after.data_type}."
                )
            ))
    return findings

def rule_nullability_changed(diff: SchemaDiff) -> List[Finding]:
    """Detect nullability constraint changes."""
    findings = []
    for change in diff.changes:
        if change.object_type == 'COLUMN' and change.change_type == 'NULLABILITY_CHANGED':
            # Changing from nullable to NOT NULL is risky
            if change.before.is_nullable and not change.after.is_nullable:
                findings.append(Finding(
                    finding_type=FindingType.COLUMN_NULLABILITY_CHANGED,
                    severity=Severity.MEDIUM,
                    base_risk=50,
                    evidence={
                        "schema": change.schema_name,
                        "table": change.table_name,
                        "column": change.column_name
                    },
                    description=(
                        f"Column '{change.column_name}' changed from NULL to "
                        f"NOT NULL."
                    )
                ))
    return findings

def rule_join_key_changed(diff: SchemaDiff,
                          sql_signals: Optional[Dict[str, Any]] = None) -> List[Finding]:
    """If column used in JOIN and changed/removed, emit HIGH severity finding."""
    findings = []
    if not sql_signals:
        return findings

    # Collect all join keys across all signals
    joining_columns = set()
    for metadata in sql_signals.values():
        if hasattr(metadata, 'join_keys'):
            for key_pair in metadata.join_keys:
                for col in key_pair:
                    joining_columns.add(col.upper())

    for change in diff.changes:
        if change.object_type == 'COLUMN' and change.column_name.upper() in joining_columns:
            if change.change_type in ('REMOVED', 'TYPE_CHANGED'):
                findings.append(Finding(
                    finding_type=FindingType.JOIN_KEY_CHANGED,
                    severity=Severity.HIGH,
                    base_risk=90,
                    evidence={
                        "schema": change.schema_name,
                        "table": change.table_name,
                        "column": change.column_name,
                        "change_type": change.change_type
                    },
                    description=(
                        f"Column '{change.column_name}' in table '{change.table_name}' "
                        f"is used as a JOIN key and was {change.change_type.lower()}. "
                        "This will likely break downstream queries."
                    )
                ))
    return findings

def rule_grain_change(diff: SchemaDiff,
                      sql_signals: Optional[Dict[str, Any]] = None) -> List[Finding]:
    """If column in GROUP BY removed, emit MEDIUM severity."""
    findings = []
    if not sql_signals:
        return findings

    grouping_columns = set()
    for metadata in sql_signals.values():
        if hasattr(metadata, 'group_by_cols'):
            for col in metadata.group_by_cols:
                grouping_columns.add(col.upper())

    for change in diff.changes:
        if (change.object_type == 'COLUMN' and
            change.change_type == 'REMOVED' and
            change.column_name.upper() in grouping_columns):
            findings.append(Finding(
                finding_type=FindingType.GRAIN_CHANGE,
                severity=Severity.MEDIUM,
                base_risk=60,
                evidence={
                    "schema": change.schema_name,
                    "table": change.table_name,
                    "column": change.column_name
                },
                description=(
                    f"Column '{change.column_name}' in table '{change.table_name}' "
                    "is used in GROUP BY clauses. Removing it will change the grain "
                    "of downstream results."
                )
            ))
    return findings

ALL_RULES = [
    rule_schema_removed,
    rule_schema_added,
    rule_table_removed,
    rule_table_added,
    rule_column_removed,
    rule_column_added,
    rule_column_type_changed,
    rule_nullability_changed,
    rule_join_key_changed,
    rule_grain_change,
    # rule_potential_breakage removed to avoid double counting
]

def apply_rules(diff: SchemaDiff,
                sql_signals: Optional[Dict[str, Any]] = None
                ) -> List[Finding]:
    """Apply all detection rules to schema diff.

    Args:
        diff: Schema differences to analyze
        sql_signals: Optional SQL metadata signals

    Returns:
        List of findings from all applicable rules
    """
    all_findings = []
    for rule in ALL_RULES:
        # Check if rule accepts sql_signals
        import inspect
        sig = inspect.signature(rule)
        if 'sql_signals' in sig.parameters:
            all_findings.extend(rule(diff, sql_signals=sql_signals))
        else:
            all_findings.extend(rule(diff))
    return all_findings
