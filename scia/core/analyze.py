"""Schema change analysis and risk assessment."""
from typing import Dict, List, Optional

from scia.core.diff import diff_schemas
from scia.core.risk import RiskAssessment
from scia.core.rules import apply_rules
from scia.models.schema import TableSchema
from scia.sql.heuristics import extract_signals

def analyze(
    before_schema: List[TableSchema],
    after_schema: List[TableSchema],
    sql_definitions: Optional[Dict[str, str]] = None
) -> RiskAssessment:
    """Core analysis orchestration.

    Args:
        before_schema: Initial schema definitions
        after_schema: Modified schema definitions
        sql_definitions: Optional SQL query definitions for signal extraction

    Returns:
        RiskAssessment with findings and classification
    """
    # 1. Diff schemas
    diff = diff_schemas(before_schema, after_schema)

    # 2. Extract SQL signals (if available)
    sql_signals = None
    if sql_definitions:
        sql_signals = extract_signals(sql_definitions)

    # 3. Apply rules
    findings = apply_rules(diff, sql_signals)

    # 4. Aggregate risk
    assessment = RiskAssessment(findings)

    return assessment
