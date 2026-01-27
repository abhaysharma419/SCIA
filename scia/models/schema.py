"""Schema models representing database structure."""
from typing import List

from pydantic import BaseModel

class ColumnSchema(BaseModel):
    """Represents a database column definition."""

    schema_name: str
    table_name: str
    column_name: str
    data_type: str
    is_nullable: bool
    ordinal_position: int

class TableSchema(BaseModel):
    """Represents a database table definition."""

    schema_name: str
    table_name: str
    columns: List[ColumnSchema]
