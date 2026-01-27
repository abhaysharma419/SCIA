import logging
from typing import List, Dict, Any, Optional
import snowflake.connector
from scia.models.schema import TableSchema, ColumnSchema

logger = logging.getLogger(__name__)

class SnowflakeInspector:
    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.conn = None

    def connect(self):
        try:
            self.conn = snowflake.connector.connect(**self.params)
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise

    def fetch_schema(self, database: str, schema: str) -> List[TableSchema]:
        """
        Fetches metadata for all tables and views in the specified schema.
        """
        if not self.conn:
            self.connect()

        try:
            cursor = self.conn.cursor()
            
            # Fetch columns metadata
            query = f"""
            SELECT 
                TABLE_SCHEMA, 
                TABLE_NAME, 
                COLUMN_NAME, 
                DATA_TYPE, 
                IS_NULLABLE, 
                ORDINAL_POSITION
            FROM {database}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{schema.upper()}'
            ORDER BY TABLE_NAME, ORDINAL_POSITION
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            # Group columns by table
            tables_data: Dict[str, List[ColumnSchema]] = {}
            for row in rows:
                table_schema_name, table_name, col_name, data_type, is_nullable, pos = row
                col = ColumnSchema(
                    schema_name=table_schema_name,
                    table_name=table_name,
                    column_name=col_name,
                    data_type=data_type,
                    is_nullable=(is_nullable == 'YES'),
                    ordinal_position=pos
                )
                if table_name not in tables_data:
                    tables_data[table_name] = []
                tables_data[table_name].append(col)

            result = []
            for table_name, columns in tables_data.items():
                result.append(TableSchema(
                    schema_name=schema,
                    table_name=table_name,
                    columns=columns
                ))
            
            return result
        except Exception as e:
            logger.warning(f"Error fetching schema metadata: {e}")
            return []

    def fetch_view_definitions(self, database: str, schema: str) -> Dict[str, str]:
        """
        Fetches definitions for all views in the specified schema.
        """
        if not self.conn:
            self.connect()

        try:
            cursor = self.conn.cursor()
            query = f"""
            SELECT TABLE_NAME, VIEW_DEFINITION
            FROM {database}.INFORMATION_SCHEMA.VIEWS
            WHERE TABLE_SCHEMA = '{schema.upper()}'
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows if row[1]}
        except Exception as e:
            logger.warning(f"Error fetching view definitions: {e}")
            return {}

    def close(self):
        if self.conn:
            self.conn.close()
