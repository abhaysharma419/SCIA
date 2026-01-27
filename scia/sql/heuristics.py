"""SQL signal extraction from query definitions."""
from typing import Dict

from scia.sql.parser import SQLMetadata, parse_sql

def extract_signals(sql_definitions: Dict[str, str]) -> Dict[str, SQLMetadata]:
    """Extract metadata signals from SQL query definitions."""
    signals = {}
    for name, sql in sql_definitions.items():
        metadata = parse_sql(sql)
        if metadata:
            signals[name] = metadata
    return signals
