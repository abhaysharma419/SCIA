"""Schema diffing and change detection."""
from typing import Any, List, Optional

from pydantic import BaseModel

from scia.models.schema import ColumnSchema, TableSchema

class SchemaChange(BaseModel):
    """Represents a change between schema versions at any level (Schema, Table, Column)."""

    object_type: str  # 'SCHEMA', 'TABLE', 'COLUMN'
    schema_name: str
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    change_type: str  # 'ADDED', 'REMOVED', 'TYPE_CHANGED', 'NULLABILITY_CHANGED'
    before: Any = None
    after: Any = None

class SchemaDiff(BaseModel):
    """Collection of all changes between two schemas."""

    changes: List[SchemaChange] = []


def diff_schemas(before: List[TableSchema], after: List[TableSchema]) -> SchemaDiff:
    """Compare two schema lists and identify changes hierarchically.

    Args:
        before: Original schema definitions
        after: Modified schema definitions

    Returns:
        SchemaDiff containing all detected changes
    """
    all_changes = []

    # Group tables by schema for hierarchy
    before_schemas = {}
    for t in before:
        before_schemas.setdefault(t.schema_name, []).append(t)
    
    after_schemas = {}
    for t in after:
        after_schemas.setdefault(t.schema_name, []).append(t)

    # 1. Schema Level Comparison
    all_schema_names = set(before_schemas.keys()) | set(after_schemas.keys())
    
    for schema_name in all_schema_names:
        b_tables = before_schemas.get(schema_name)
        a_tables = after_schemas.get(schema_name)

        if b_tables and not a_tables:
            all_changes.append(SchemaChange(
                object_type='SCHEMA',
                schema_name=schema_name,
                change_type='REMOVED'
            ))
            continue
        
        if not b_tables and a_tables:
            all_changes.append(SchemaChange(
                object_type='SCHEMA',
                schema_name=schema_name,
                change_type='ADDED'
            ))
            continue

        # 2. Table Level Comparison (if schema exists in both)
        before_table_map = {t.table_name: t for t in b_tables}
        after_table_map = {t.table_name: t for t in a_tables}
        
        all_table_names = set(before_table_map.keys()) | set(after_table_map.keys())
        
        for table_name in all_table_names:
            b_table = before_table_map.get(table_name)
            a_table = after_table_map.get(table_name)

            if b_table and not a_table:
                all_changes.append(SchemaChange(
                    object_type='TABLE',
                    schema_name=schema_name,
                    table_name=table_name,
                    change_type='REMOVED'
                ))
                continue
            
            if not b_table and a_table:
                all_changes.append(SchemaChange(
                    object_type='TABLE',
                    schema_name=schema_name,
                    table_name=table_name,
                    change_type='ADDED'
                ))
                continue

            # 3. Column Level Comparison (if table exists in both)
            _process_column_level_diff(schema_name, table_name, b_table, a_table, all_changes)

    return SchemaDiff(changes=all_changes)

def _process_column_level_diff(schema_name: str, table_name: str, 
                             before_table: TableSchema, after_table: TableSchema,
                             changes: list) -> None:
    """Compare columns within a table that exists in both versions."""
    before_cols = {c.column_name: c for c in before_table.columns}
    after_cols = {c.column_name: c for c in after_table.columns}

    all_col_names = set(before_cols.keys()) | set(after_cols.keys())

    for col_name in all_col_names:
        b_col = before_cols.get(col_name)
        a_col = after_cols.get(col_name)

        if b_col and not a_col:
            changes.append(SchemaChange(
                object_type='COLUMN',
                schema_name=schema_name,
                table_name=table_name,
                column_name=col_name,
                change_type='REMOVED',
                before=b_col
            ))
        elif not b_col and a_col:
            changes.append(SchemaChange(
                object_type='COLUMN',
                schema_name=schema_name,
                table_name=table_name,
                column_name=col_name,
                change_type='ADDED',
                after=a_col
            ))
        elif b_col and a_col:
            # Check for type change
            if b_col.data_type != a_col.data_type:
                changes.append(SchemaChange(
                    object_type='COLUMN',
                    schema_name=schema_name,
                    table_name=table_name,
                    column_name=col_name,
                    change_type='TYPE_CHANGED',
                    before=b_col,
                    after=a_col
                ))
            # Check for nullability change
            elif b_col.is_nullable != a_col.is_nullable:
                changes.append(SchemaChange(
                    object_type='COLUMN',
                    schema_name=schema_name,
                    table_name=table_name,
                    column_name=col_name,
                    change_type='NULLABILITY_CHANGED',
                    before=b_col,
                    after=a_col
                ))
