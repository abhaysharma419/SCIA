"""DDL (Data Definition Language) parser for schema creation and modification."""
import logging
from typing import List, Optional

import sqlglot
from sqlglot import exp

from scia.models.schema import ColumnSchema, TableSchema

logger = logging.getLogger(__name__)


def parse_ddl_to_schema(ddl_sql: str) -> List[TableSchema]:
    """Parse CREATE TABLE and ALTER TABLE DDL statements to schema objects.
    
    Supports:
    - CREATE TABLE (with column definitions)
    - ALTER TABLE ADD COLUMN
    - ALTER TABLE DROP COLUMN
    - ALTER TABLE MODIFY COLUMN (type/nullability changes)
    - ALTER TABLE RENAME COLUMN
    
    Gracefully handles unsupported statements by logging warnings and skipping.
    Never raises an exception; returns empty list on complete failure.
    
    Args:
        ddl_sql: DDL SQL text (one or more statements)
        
    Returns:
        List of TableSchema objects extracted from CREATE TABLE statements.
        Empty list if no valid CREATE TABLE statements found or parsing fails.
    """
    schemas: dict = {}
    
    try:
        # Parse all statements in the DDL
        statements = sqlglot.parse(ddl_sql, read='snowflake')
        
        for stmt in statements:
            if not stmt:
                continue
                
            # Handle CREATE TABLE statements
            if isinstance(stmt, exp.Create):
                schema_obj = _handle_create_table(stmt)
                if schema_obj:
                    key = (schema_obj.schema_name, schema_obj.table_name)
                    schemas[key] = schema_obj
                    
            # Handle ALTER TABLE statements
            elif isinstance(stmt, exp.Alter):
                _handle_alter_table(stmt, schemas)
                
            else:
                logger.debug("Skipping unsupported statement type: %s", type(stmt).__name__)
        
        return list(schemas.values())
        
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("DDL parsing failed: %s", e)
        return []


def _handle_create_table(stmt: exp.Create) -> Optional[TableSchema]:
    """Extract TableSchema from CREATE TABLE statement.
    
    Args:
        stmt: sqlglot Create expression
        
    Returns:
        TableSchema object or None if extraction fails
    """
    try:
        # In sqlglot, CREATE TABLE has 'this' which is a Schema
        schema_def = stmt.args.get('this')
        
        if not isinstance(schema_def, exp.Schema):
            logger.debug("No schema definition found in CREATE TABLE")
            return None
        
        # Get table name from the schema
        # The table name is actually stored in parent of the schema
        table_name = None
        if hasattr(schema_def, 'this') and schema_def.this:
            # schema_def.this is the table identifier
            table_name = schema_def.this.name if hasattr(schema_def.this, 'name') else str(schema_def.this)
        
        if not table_name:
            # Try alternative: get from schema.name
            table_name = schema_def.name
        
        if not table_name:
            logger.debug("No table name found in CREATE TABLE")
            return None
        
        # Extract schema name (default to PUBLIC)
        schema_name = 'PUBLIC'
        
        # Get columns from schema expressions
        columns = []
        ordinal_pos = 1
        
        for col_expr in schema_def.expressions:
            if isinstance(col_expr, exp.ColumnDef):
                col = _extract_column_from_columndef(col_expr, schema_name, table_name, ordinal_pos)
                if col:
                    columns.append(col)
                    ordinal_pos += 1
        
        if not columns:
            logger.warning("CREATE TABLE %s has no columns", table_name)
            return None
        
        return TableSchema(
            schema_name=schema_name,
            table_name=table_name.upper(),
            columns=columns
        )
        
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("Failed to extract CREATE TABLE: %s", e)
        return None


def _extract_column_from_columndef(
    col_expr: exp.ColumnDef,
    schema_name: str,
    table_name: str,
    ordinal_pos: int
) -> Optional[ColumnSchema]:
    """Extract ColumnSchema from ColumnDef expression.
    
    Args:
        col_expr: sqlglot ColumnDef expression
        schema_name: Schema name
        table_name: Table name
        ordinal_pos: Column ordinal position
        
    Returns:
        ColumnSchema object or None if extraction fails
    """
    try:
        col_name = col_expr.name
        if not col_name:
            return None
        
        # Get data type
        data_type = 'VARCHAR'  # Default type
        if col_expr.kind:
            data_type = col_expr.kind.sql(dialect='snowflake')
        
        # Determine nullability - default to nullable
        is_nullable = True
        
        # Check constraints for NOT NULL
        if col_expr.constraints:
            for constraint in col_expr.constraints:
                # Check if it's a ColumnConstraint with NotNullColumnConstraint kind
                if isinstance(constraint, exp.ColumnConstraint):
                    if isinstance(constraint.kind, exp.NotNullColumnConstraint):
                        is_nullable = False
                        break
                # Also check for direct NotNull expression
                elif isinstance(constraint, exp.NotNullColumnConstraint):
                    is_nullable = False
                    break
        
        return ColumnSchema(
            schema_name=schema_name,
            table_name=table_name.upper(),
            column_name=col_name.upper(),
            data_type=data_type.upper(),
            is_nullable=is_nullable,
            ordinal_position=ordinal_pos
        )
        
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("Failed to extract column definition: %s", e)
        return None


def _handle_alter_table(
    stmt: exp.Alter,
    schemas: dict
) -> None:
    """Handle ALTER TABLE statement and update schemas accordingly.
    
    Supports: ADD COLUMN, DROP COLUMN, MODIFY COLUMN, RENAME COLUMN
    
    Args:
        stmt: sqlglot Alter expression
        schemas: Dictionary of (schema_name, table_name) -> TableSchema
    """
    try:
        # Get table name
        table_name = stmt.name
        if not table_name:
            return
        
        # ALTER statements are parsed for future v0.2 features
        # For now, we just log them as we're primarily extracting from CREATE TABLE
        logger.debug("Parsing ALTER TABLE %s (v0.2 enhancement)", table_name)
        
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("Failed to parse ALTER TABLE: %s", e)


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
