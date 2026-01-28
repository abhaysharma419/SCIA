"""SQL parsing and metadata extraction."""
import logging
from typing import List, Optional, Set

import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

class SQLMetadata:  # pylint: disable=too-few-public-methods
    """Extracted metadata from SQL query."""

    def __init__(self):
        """Initialize metadata containers."""
        self.tables: Set[str] = set()
        self.columns: Set[str] = set()
        self.join_keys: List[tuple] = []
        self.group_by_cols: Set[str] = set()

def _extract_metadata(expression: exp.Expression, metadata: SQLMetadata):
    """Internal helper to extract metadata from a single expression."""
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
        _extract_join_keys(join, metadata)

def _extract_join_keys(join: exp.Join, metadata: SQLMetadata):
    """Internal helper to extract join keys from a join expression."""
    on_clause = join.args.get("on")
    if not on_clause:
        return
    for eq_expr in on_clause.find_all(exp.EQ):
        cols = [c.name.upper() for c in eq_expr.find_all(exp.Column)]
        if len(cols) == 2:
            metadata.join_keys.append(tuple(cols))

def parse_sql(sql: str) -> Optional[SQLMetadata]:
    """Best-effort SQL parsing for structural signals.

    Never raises fatal exception, returns None on failure.
    """
    try:
        metadata = SQLMetadata()
        # Using snowflake dialect as default for v0.1
        for expression in sqlglot.parse(sql, read="snowflake"):
            if expression:
                _extract_metadata(expression, metadata)
        return metadata
    except (AttributeError, ValueError, TypeError) as e:
        logger.warning("SQL parsing failed: %s", e)
        return None

def extract_table_references(sql: str, dialect: str = 'snowflake') -> List[str]:
    """Extract all table references from a SQL query.

    Args:
        sql: SQL query text
        dialect: SQL dialect (default: snowflake)

    Returns:
        List of table names referenced in qualified format (schema.table or just table).
        Empty list if parsing fails.
    """
    try:
        statements = sqlglot.parse(sql, read=dialect)
        tables = set()

        for stmt in statements:
            if not stmt:
                continue

            for table in stmt.find_all(exp.Table):
                # Get fully qualified table name
                if hasattr(table, 'db') and table.db:
                    qualified_name = f"{table.db}.{table.name}".upper()
                else:
                    qualified_name = table.name.upper()

                tables.add(qualified_name)

        return sorted(list(tables))

    except Exception as e:  # pylint: disable=broad-except
        logger.warning("Failed to extract table references: %s", e)
        return []
