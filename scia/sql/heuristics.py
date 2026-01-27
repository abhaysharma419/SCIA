from typing import List, Dict, Any
from scia.sql.parser import parse_sql, SQLMetadata

def extract_signals(sql_definitions: Dict[str, str]) -> Dict[str, SQLMetadata]:
    """
    Analyzes multiple SQL definitions and extracts signals.
    """
    signals = {}
    for name, sql in sql_definitions.items():
        metadata = parse_sql(sql)
        if metadata:
            signals[name] = metadata
    return signals
