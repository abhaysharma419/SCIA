"""Detection rules for schema changes."""
from typing import Any, Dict, List, Optional

from scia.core.diff import SchemaDiff
from scia.models.finding import Finding, FindingType, Severity

def rule_column_removed(diff: SchemaDiff) -> List[Finding]:
    """Detect removed columns."""
    findings = []
    for change in diff.column_changes:
        if change.change_type == 'REMOVED':
            findings.append(Finding(
                finding_type=FindingType.COLUMN_REMOVED,
                severity=Severity.HIGH,
                base_risk=80,
                evidence={"table": change.table_name, "column": change.column_name},
                description=(
                    f"Column '{change.column_name}' removed from table "
                    f"'{change.table_name}'."
                )
            ))
    return findings

def rule_column_type_changed(diff: SchemaDiff) -> List[Finding]:
    """Detect column type changes."""
    findings = []
    for change in diff.column_changes:
        if change.change_type == 'TYPE_CHANGED':
            findings.append(Finding(
                finding_type=FindingType.COLUMN_TYPE_CHANGED,
                severity=Severity.MEDIUM,
                base_risk=40,
                evidence={
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
    for change in diff.column_changes:
        if change.change_type == 'NULLABILITY_CHANGED':
            # Changing from nullable to NOT NULL is risky
            if change.before.is_nullable and not change.after.is_nullable:
                findings.append(Finding(
                    finding_type=FindingType.COLUMN_NULLABILITY_CHANGED,
                    severity=Severity.MEDIUM,
                    base_risk=50,
                    evidence={
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
    # sql_signals is Dict[str, SQLMetadata]
    joining_columns = set()
    for metadata in sql_signals.values():
        if hasattr(metadata, 'join_keys'):
            for key_pair in metadata.join_keys:
                for col in key_pair:
                    joining_columns.add(col.upper())

    for change in diff.column_changes:
        if change.column_name.upper() in joining_columns:
            if change.change_type in ('REMOVED', 'TYPE_CHANGED'):
                findings.append(Finding(
                    finding_type=FindingType.JOIN_KEY_CHANGED,
                    severity=Severity.HIGH,
                    base_risk=90,
                    evidence={
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

    for change in diff.column_changes:
        if (change.change_type == 'REMOVED' and
            change.column_name.upper() in grouping_columns):
            findings.append(Finding(
                finding_type=FindingType.GRAIN_CHANGE,
                severity=Severity.MEDIUM,
                base_risk=60,
                evidence={
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

def rule_potential_breakage(diff: SchemaDiff,
                            sql_signals: Optional[Dict[str, Any]] = None) -> List[Finding]:
    """Catch-all for complex changes. MEDIUM severity."""
    findings = []
    referenced_columns = set()
    if sql_signals:
        for metadata in sql_signals.values():
            if hasattr(metadata, 'columns'):
                for col in metadata.columns:
                    referenced_columns.add(col.upper())

    for change in diff.column_changes:
        if change.change_type == 'TYPE_CHANGED':
            # If we have SQL signals, only flag if the column is actually referenced
            if not sql_signals or change.column_name.upper() in referenced_columns:
                findings.append(Finding(
                    finding_type=FindingType.POTENTIAL_BREAKAGE,
                    severity=Severity.MEDIUM,
                    base_risk=50,
                    evidence={
                        "table": change.table_name,
                        "column": change.column_name,
                        "before": change.before.data_type,
                        "after": change.after.data_type
                    },
                    description=(
                        f"Type change for column '{change.column_name}' in table "
                        f"'{change.table_name}' ({change.before.data_type} -> "
                        f"{change.after.data_type}) may cause downstream issues."
                    )
                ))
    return findings

ALL_RULES = [
    rule_column_removed,
    rule_column_type_changed,
    rule_nullability_changed,
    rule_join_key_changed,
    rule_grain_change,
    rule_potential_breakage
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
