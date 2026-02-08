"""DDL (Data Definition Language) parser for schema creation and modification."""
import logging
import re
from typing import Callable, Dict, List, Optional

import sqlglot
from sqlglot import exp

from scia.models.schema import ColumnSchema, TableSchema

logger = logging.getLogger(__name__)

# Registry of dialect-specific preprocessors
# Key: dialect name (e.g., 'snowflake', 'postgres', etc.)
# Value: List of preprocessor functions
_DIALECT_PREPROCESSORS: Dict[str, List[Callable[[str], str]]] = {}


def register_dialect_preprocessor(dialect: str, func: Callable[[str], str]) -> None:
    """Register a dialect-specific SQL preprocessor.
    
    This allows extending support for dialect-specific syntax that sqlglot
    doesn't natively handle. Preprocessors run before sqlglot parsing to
    convert dialect-specific syntax to standard forms.
    
    Args:
        dialect: SQL dialect name (e.g., 'snowflake', 'postgres')
        func: Preprocessor function that takes SQL string and returns modified SQL
        
    Example:
        @register_dialect_preprocessor('snowflake')
        def fix_snowflake_syntax(sql: str) -> str:
            # Convert Snowflake-specific syntax
            return sql.replace('SOMETHING', 'STANDARD')
    """
    if dialect not in _DIALECT_PREPROCESSORS:
        _DIALECT_PREPROCESSORS[dialect] = []
    _DIALECT_PREPROCESSORS[dialect].append(func)
    logger.debug("Registered preprocessor for dialect '%s': %s", dialect, func.__name__)


def _preprocess_sql(sql: str, dialect: str) -> str:
    """Apply dialect-specific preprocessors to SQL.
    
    Args:
        sql: Original SQL text
        dialect: SQL dialect name
        
    Returns:
        Modified SQL with dialect-specific syntax converted to standard forms
    """
    if dialect not in _DIALECT_PREPROCESSORS:
        return sql
    
    original_sql = sql
    for preprocessor in _DIALECT_PREPROCESSORS[dialect]:
        try:
            sql = preprocessor(sql)
        except Exception as e:
            logger.warning("Preprocessor %s failed: %s", preprocessor.__name__, e)
    
    if sql != original_sql:
        logger.debug("SQL was modified by preprocessor for dialect '%s'", dialect)
    
    return sql


def _preprocess_snowflake_modify_column(sql: str) -> str:
    """Convert Snowflake 'ALTER TABLE ... MODIFY COLUMN' to standard 'ALTER TABLE ... ALTER COLUMN ... TYPE'.
    
    Snowflake supports both syntaxes, but sqlglot only parses the ALTER COLUMN form.
    This preprocessor converts MODIFY COLUMN syntax to the standard form.
    
    Examples:
        ALTER TABLE t MODIFY COLUMN c VARCHAR(255) -> ALTER TABLE t ALTER COLUMN c TYPE VARCHAR(255)
        ALTER TABLE t MODIFY c VARCHAR(255) -> ALTER TABLE t ALTER COLUMN c TYPE VARCHAR(255)
    
    Args:
        sql: SQL potentially containing MODIFY COLUMN statements
        
    Returns:
        SQL with MODIFY COLUMN converted to ALTER COLUMN TYPE
    """
    # Pattern: ALTER TABLE <table> MODIFY [COLUMN] <col_name> <data_type>
    # Matches: ALTER TABLE ... MODIFY COLUMN col_name type or ALTER TABLE ... MODIFY col_name type
    pattern = re.compile(
        r'ALTER\s+TABLE\s+(\S+)\s+MODIFY(?:\s+COLUMN)?\s+(\S+)\s+(\S+(?:\([^)]*\))?)',
        re.IGNORECASE
    )
    
    def replace_match(match):
        table_name = match.group(1)
        column_name = match.group(2)
        data_type = match.group(3)
        # Convert to: ALTER TABLE table_name ALTER COLUMN column_name TYPE data_type
        return f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {data_type}"
    
    modified_sql = pattern.sub(replace_match, sql)
    
    if modified_sql != sql:
        logger.debug("Converted MODIFY COLUMN to ALTER COLUMN TYPE syntax")
    
    return modified_sql


# Register Snowflake preprocessor
register_dialect_preprocessor('snowflake', _preprocess_snowflake_modify_column)


def parse_ddl_to_schema(
    ddl_sql: str,
    base_schemas: Optional[List[TableSchema]] = None,
    dialect: str = 'snowflake'
) -> List[TableSchema]:
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
        base_schemas: Optional list of base schemas for ALTER TABLE operations
        dialect: SQL dialect for parsing (default: 'snowflake')

    Returns:
        List of TableSchema objects extracted from CREATE TABLE and ALTER TABLE statements.
    """
    schemas: dict = {}

    # Seed with base schemas if provided
    if base_schemas:
        for schema in base_schemas:
            key = (schema.schema_name or 'PUBLIC', schema.table_name)
            schemas[key] = schema.model_copy(deep=True)

    try:
        # Preprocess SQL for dialect-specific syntax
        # This converts unsupported syntax to standard forms before sqlglot parsing
        processed_sql = _preprocess_sql(ddl_sql, dialect)
        
        # Parse all statements in the DDL
        statements = sqlglot.parse(processed_sql, read=dialect)

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
                logger.debug("Statement SQL: %s", stmt.sql())

        return list(schemas.values())

    except Exception as e:  # pylint: disable=broad-except
        logger.warning("DDL parsing failed: %s", e)
        return []


def _handle_create_table(stmt: exp.Create) -> Optional[TableSchema]:
    """Extract TableSchema from CREATE TABLE statement."""
    try:
        # In sqlglot, CREATE TABLE has 'this' which is a Schema
        schema_def = stmt.args.get('this')
        if not isinstance(schema_def, exp.Schema):
            logger.debug("No schema definition found in CREATE TABLE")
            return None

        # Get table and schema from the schema definition
        table_schema = schema_def.this
        if not isinstance(table_schema, exp.Table):
            logger.debug("No table definition found in CREATE TABLE")
            return None

        table_context = _extract_table_context(table_schema)
        if not table_context:
            return None

        table_name, schema_name, db_name = table_context

        # Extract columns from schema expressions
        columns = _extract_columns_from_schema(schema_def, schema_name, table_name, db_name)

        if not columns:
            logger.warning("CREATE TABLE %s has no columns", table_name)
            return None

        return TableSchema(
            database_name=db_name,
            schema_name=schema_name,
            table_name=table_name,
            columns=columns
        )

    except Exception as e:  # pylint: disable=broad-except
        logger.warning("Failed to extract CREATE TABLE: %s", e)
        return None

def _extract_table_context(table_schema: exp.Table):
    """Extract table name, schema, and db from table expression."""
    if hasattr(table_schema.this, 'name'):
        table_name = table_schema.this.name
    else:
        table_name = str(table_schema.this)

    if not table_name:
        logger.debug("No table name found in CREATE TABLE")
        return None

    schema_name = table_schema.db
    if hasattr(schema_name, 'name'):
        schema_name = schema_name.name
    if not schema_name or str(schema_name).upper() == 'NONE':
        schema_name = 'PUBLIC'

    target_db_name = None
    database_name = table_schema.catalog
    if database_name:
        target_db_name = (
            database_name.name if hasattr(database_name, 'name')
            else str(database_name)
        )
        target_db_name = target_db_name.upper()

    return table_name.upper(), schema_name.upper(), target_db_name

def _extract_columns_from_schema(schema_def, schema_name, table_name, db_name):
    """Extract list of ColumnSchema from schema definition."""
    columns = []
    ordinal_pos = 1

    for col_expr in schema_def.expressions:
        if isinstance(col_expr, exp.ColumnDef):
            col = _extract_column_from_columndef(
                col_expr, schema_name, table_name,
                ordinal_pos, db_name=db_name
            )
            if col:
                columns.append(col)
                ordinal_pos += 1
    return columns


def _extract_column_from_columndef(
    col_expr: exp.ColumnDef,
    schema_name: str,
    table_name: str,
    ordinal_pos: int,
    db_name: Optional[str] = None
) -> Optional[ColumnSchema]:
    """Extract ColumnSchema from ColumnDef expression.

    Args:
        col_expr: sqlglot ColumnDef expression
        schema_name: Schema name
        table_name: Table name
        ordinal_pos: Column ordinal position
        db_name: Optional database name

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
            database_name=db_name.upper() if db_name else None,
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


def _handle_alter_actions(
    stmt: exp.Alter,
    table_schema: TableSchema,
    schema_name: str,
    table_name: str
) -> None:
    """Process specific actions within an ALTER TABLE statement."""
    for action in stmt.args.get('actions', []):
        if isinstance(action, exp.ColumnDef):
            _handle_add_column(action, table_schema, schema_name, table_name)
        elif isinstance(action, exp.Drop) and action.args.get('kind') == 'COLUMN':
            _handle_drop_column(action, table_schema)
        elif isinstance(action, exp.RenameColumn):
            _handle_rename_column(action, table_schema)
        elif isinstance(action, exp.AlterColumn):
            _handle_modify_column(action, table_schema)


def _handle_add_column(
    action: exp.ColumnDef,
    table_schema: TableSchema,
    schema_name: str,
    table_name: str
) -> None:
    """Handle ADD COLUMN action."""
    new_col = _extract_column_from_columndef(
        action, schema_name, table_name, len(table_schema.columns) + 1
    )
    if new_col:
        table_schema.columns.append(new_col)


def _handle_drop_column(action: exp.Drop, table_schema: TableSchema) -> None:
    """Handle DROP COLUMN action."""
    col_name = action.this.name.upper()
    table_schema.columns = [
        c for c in table_schema.columns
        if c.column_name.upper() != col_name
    ]


def _handle_rename_column(action: exp.RenameColumn, table_schema: TableSchema) -> None:
    """Handle RENAME COLUMN action."""
    old_name = action.this.name.upper()
    new_name = action.args.get('to').name.upper()
    for col in table_schema.columns:
        if col.column_name.upper() == old_name:
            col.column_name = new_name


def _handle_modify_column(action: exp.AlterColumn, table_schema: TableSchema) -> None:
    """Handle MODIFY/ALTER COLUMN action."""
    col_name = action.this.name.upper()
    for col in table_schema.columns:
        if col.column_name.upper() == col_name:
            # Update type if provided
            dtype = action.args.get('dtype')
            if dtype:
                col.data_type = dtype.sql(dialect='snowflake').upper()

            # Update nullability if provided
            allow_null = action.args.get('allow_null')
            if allow_null is not None:
                col.is_nullable = bool(allow_null)


def _get_table_key(stmt: exp.Alter) -> tuple:
    """Extract schema and table name key from ALTER statement."""
    table_expr = stmt.this
    if not isinstance(table_expr, exp.Table):
        return None, None

    # Extract table and schema names robustly
    if hasattr(table_expr.this, 'name'):
        table_name = table_expr.this.name
    else:
        table_name = str(table_expr.this)

    schema_name = table_expr.db
    if hasattr(schema_name, 'name'):
        schema_name = schema_name.name
    if not schema_name or str(schema_name).upper() == 'NONE':
        schema_name = 'PUBLIC'

    return schema_name.upper(), table_name.upper()


def _handle_alter_table(
    stmt: exp.Alter,
    schemas: dict
) -> None:
    """Handle ALTER TABLE statement and update schemas accordingly.

    Supports: ADD COLUMN, DROP COLUMN, MODIFY COLUMN, RENAME COLUMN
    """
    try:
        schema_name, table_name = _get_table_key(stmt)
        if not schema_name or not table_name:
            return

        key = (schema_name, table_name)

        if key not in schemas:
            logger.debug("Table %s.%s not found for ALTER", schema_name, table_name)
            return

        _handle_alter_actions(stmt, schemas[key], schema_name, table_name)

    except Exception as e:  # pylint: disable=broad-except
        logger.warning("Failed to parse ALTER TABLE: %s", e)


