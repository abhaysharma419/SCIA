from pydantic import BaseModel
from typing import List, Optional

class ColumnSchema(BaseModel):
    schema_name: str
    table_name: str
    column_name: str
    data_type: str
    is_nullable: bool
    ordinal_position: int

class TableSchema(BaseModel):
    schema_name: str
    table_name: str
    columns: List[ColumnSchema]
