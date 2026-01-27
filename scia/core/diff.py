"""Schema diffing and change detection."""
from typing import List, Optional

from pydantic import BaseModel

from scia.models.schema import ColumnSchema, TableSchema

class ColumnDiff(BaseModel):
    """Represents a single column change between schema versions."""

    schema_name: str
    table_name: str
    column_name: str
    change_type: str  # 'ADDED', 'REMOVED', 'TYPE_CHANGED', 'NULLABILITY_CHANGED'
    before: Optional[ColumnSchema] = None
    after: Optional[ColumnSchema] = None

class SchemaDiff(BaseModel):
    """Collection of all column changes between two schemas."""

    column_changes: List[ColumnDiff] = []


def diff_schemas(before: List[TableSchema], after: List[TableSchema]) -> SchemaDiff:
    """Compare two schema lists and identify column changes.

    Args:
        before: Original schema definitions
        after: Modified schema definitions

    Returns:
        SchemaDiff containing all detected column changes
    """
    column_changes = []

    # Map tables by name for easy lookup
    before_map = {t.table_name: t for t in before}
    after_map = {t.table_name: t for t in after}

    for table_name in set(before_map.keys()) | set(after_map.keys()):
        _process_table_diff(table_name, before_map, after_map, column_changes)

    return SchemaDiff(column_changes=column_changes)

def _process_table_diff(table_name: str, before_map: dict, after_map: dict,
                       changes: list) -> None:
    """Process changes for a single table."""
    before_table = before_map.get(table_name)
    after_table = after_map.get(table_name)

    # If table is removed, all its columns are removed
    if before_table and not after_table:
        for col in before_table.columns:
            changes.append(ColumnDiff(
                schema_name=col.schema_name,
                table_name=table_name,
                column_name=col.column_name,
                change_type='REMOVED',
                before=col
            ))
        return

    # If table is added, all its columns are added
    if not before_table and after_table:
        for col in after_table.columns:
            changes.append(ColumnDiff(
                schema_name=col.schema_name,
                table_name=table_name,
                column_name=col.column_name,
                change_type='ADDED',
                after=col
            ))
        return

    # Table exists in both, compare columns
    if before_table and after_table:
        before_cols = {c.column_name: c for c in before_table.columns}
        after_cols = {c.column_name: c for c in after_table.columns}

        for col_name in set(before_cols.keys()) | set(after_cols.keys()):
            _process_col_diff(col_name, table_name, before_cols,
                            after_cols, changes)

def _process_col_diff(col_name: str, table_name: str, before_cols: dict,
                     after_cols: dict, changes: list) -> None:
    """Process changes for a single column."""
    b_col = before_cols.get(col_name)
    a_col = after_cols.get(col_name)

    if b_col and not a_col:
        changes.append(ColumnDiff(
            schema_name=b_col.schema_name,
            table_name=table_name,
            column_name=col_name,
            change_type='REMOVED',
            before=b_col
        ))
    elif not b_col and a_col:
        changes.append(ColumnDiff(
            schema_name=a_col.schema_name,
            table_name=table_name,
            column_name=col_name,
            change_type='ADDED',
            after=a_col
        ))
    elif b_col and a_col and b_col.data_type != a_col.data_type:
        # Type changed
        changes.append(ColumnDiff(
            schema_name=b_col.schema_name,
            table_name=table_name,
            column_name=col_name,
            change_type='TYPE_CHANGED',
            before=b_col,
            after=a_col
        ))
    elif b_col and a_col and b_col.is_nullable != a_col.is_nullable:
        # Nullability changed
        changes.append(ColumnDiff(
            schema_name=b_col.schema_name,
            table_name=table_name,
            column_name=col_name,
            change_type='NULLABILITY_CHANGED',
            before=b_col,
            after=a_col
        ))
