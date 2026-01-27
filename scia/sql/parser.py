import logging
from typing import List, Optional, Set
import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

class SQLMetadata:
    def __init__(self):
        self.tables: Set[str] = set()
        self.columns: Set[str] = set()
        self.join_keys: List[tuple] = []
        self.group_by_cols: Set[str] = set()

def parse_sql(sql: str) -> Optional[SQLMetadata]:
    """
    Best-effort parsing of SQL to extract structural signals.
    Never raises fatal exception.
    """
    try:
        metadata = SQLMetadata()
        # Using snowflake dialect as default for v0.1
        for expression in sqlglot.parse(sql, read="snowflake"):
            if not expression:
                continue
            
            # Extract tables
            for table in expression.find_all(exp.Table):
                metadata.tables.add(table.name.upper())
            
            # Extract columns
            for column in expression.find_all(exp.Column):
                metadata.columns.add(column.name.upper())
                
            # Extract group by columns
            for group in expression.find_all(exp.Group):
                for col in group.find_all(exp.Column):
                    metadata.group_by_cols.add(col.name.upper())

            # Extract join keys (simplified for v0.1)
            for join in expression.find_all(exp.Join):
                on_clause = join.args.get("on")
                if on_clause:
                    for eq in on_clause.find_all(exp.EQ):
                        cols = [c.name.upper() for c in eq.find_all(exp.Column)]
                        if len(cols) == 2:
                            metadata.join_keys.append(tuple(cols))
        
        return metadata
    except Exception as e:
        logger.warning(f"SQL parsing failed: {e}")
        return None
