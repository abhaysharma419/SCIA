from typing import List, Optional, Set, Dict
from pydantic import BaseModel
from scia.models.schema import TableSchema, ColumnSchema

class ColumnDiff(BaseModel):
    schema_name: str
    table_name: str
    column_name: str
    change_type: str  # 'ADDED', 'REMOVED', 'TYPE_CHANGED', 'NULLABILITY_CHANGED'
    before: Optional[ColumnSchema] = None
    after: Optional[ColumnSchema] = None

class SchemaDiff(BaseModel):
    column_changes: List[ColumnDiff] = []

def diff_schemas(before: List[TableSchema], after: List[TableSchema]) -> SchemaDiff:
    """
    Compares two lists of TableSchema objects and returns structural deltas.
    """
    column_changes = []
    
    # Map tables by name for easy lookup
    before_map = {t.table_name: t for t in before}
    after_map = {t.table_name: t for t in after}
    
    all_tables = set(before_map.keys()) | set(after_map.keys())
    
    for table_name in all_tables:
        before_table = before_map.get(table_name)
        after_table = after_map.get(table_name)
        
        # If table is removed, all its columns are removed
        if before_table and not after_table:
            for col in before_table.columns:
                column_changes.append(ColumnDiff(
                    schema_name=col.schema_name,
                    table_name=table_name,
                    column_name=col.column_name,
                    change_type='REMOVED',
                    before=col
                ))
            continue
            
        # If table is added, all its columns are added
        if not before_table and after_table:
            for col in after_table.columns:
                column_changes.append(ColumnDiff(
                    schema_name=col.schema_name,
                    table_name=table_name,
                    column_name=col.column_name,
                    change_type='ADDED',
                    after=col
                ))
            continue

        # Table exists in both, compare columns
        if before_table and after_table:
            before_cols = {c.column_name: c for c in before_table.columns}
            after_cols = {c.column_name: c for c in after_table.columns}
            
            all_cols = set(before_cols.keys()) | set(after_cols.keys())
            
            for col_name in all_cols:
                b_col = before_cols.get(col_name)
                a_col = after_cols.get(col_name)
                
                if b_col and not a_col:
                    column_changes.append(ColumnDiff(
                        schema_name=b_col.schema_name,
                        table_name=table_name,
                        column_name=col_name,
                        change_type='REMOVED',
                        before=b_col
                    ))
                elif not b_col and a_col:
                    column_changes.append(ColumnDiff(
                        schema_name=a_col.schema_name,
                        table_name=table_name,
                        column_name=col_name,
                        change_type='ADDED',
                        after=a_col
                    ))
                elif b_col and a_col:
                    # Check for changes in type or nullability
                    if b_col.data_type != a_col.data_type:
                        column_changes.append(ColumnDiff(
                            schema_name=b_col.schema_name,
                            table_name=table_name,
                            column_name=col_name,
                            change_type='TYPE_CHANGED',
                            before=b_col,
                            after=a_col
                        ))
                    elif b_col.is_nullable != a_col.is_nullable:
                        column_changes.append(ColumnDiff(
                            schema_name=b_col.schema_name,
                            table_name=table_name,
                            column_name=col_name,
                            change_type='NULLABILITY_CHANGED',
                            before=b_col,
                            after=a_col
                        ))
                        
    return SchemaDiff(column_changes=column_changes)
