from typing import List, Optional, Dict, Any
from scia.core.diff import SchemaDiff, ColumnDiff
from scia.models.finding import Finding, FindingType, Severity

def rule_column_removed(diff: SchemaDiff) -> List[Finding]:
    findings = []
    for change in diff.column_changes:
        if change.change_type == 'REMOVED':
            findings.append(Finding(
                finding_type=FindingType.COLUMN_REMOVED,
                severity=Severity.HIGH,
                base_risk=80,
                evidence={"table": change.table_name, "column": change.column_name},
                description=f"Column '{change.column_name}' was removed from table '{change.table_name}'."
            ))
    return findings

def rule_column_type_changed(diff: SchemaDiff) -> List[Finding]:
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
                description=f"Column '{change.column_name}' type changed from {change.before.data_type} to {change.after.data_type}."
            ))
    return findings

def rule_nullability_changed(diff: SchemaDiff) -> List[Finding]:
    findings = []
    for change in diff.column_changes:
        if change.change_type == 'NULLABILITY_CHANGED':
            # Changing from nullable to NOT NULL is risky
            if change.before.is_nullable and not change.after.is_nullable:
                findings.append(Finding(
                    finding_type=FindingType.COLUMN_NULLABILITY_CHANGED,
                    severity=Severity.MEDIUM,
                    base_risk=50,
                    evidence={"table": change.table_name, "column": change.column_name},
                    description=f"Column '{change.column_name}' changed from NULL to NOT NULL."
                ))
    return findings

ALL_RULES = [
    rule_column_removed,
    rule_column_type_changed,
    rule_nullability_changed
]

def apply_rules(diff: SchemaDiff, sql_signals: Optional[Dict[str, Any]] = None) -> List[Finding]:
    all_findings = []
    for rule in ALL_RULES:
        # v0.1 rules only consume diffs for now
        all_findings.extend(rule(diff))
    return all_findings
