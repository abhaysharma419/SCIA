from typing import List, Optional, Dict, Any
from scia.models.schema import TableSchema
from scia.core.diff import diff_schemas
from scia.core.rules import apply_rules
from scia.core.risk import RiskAssessment
from scia.sql.heuristics import extract_signals

def analyze(
    before_schema: List[TableSchema],
    after_schema: List[TableSchema],
    sql_definitions: Optional[Dict[str, str]] = None
) -> RiskAssessment:
    """
    Core analysis orchestration.
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
