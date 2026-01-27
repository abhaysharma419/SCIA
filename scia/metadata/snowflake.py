"""Snowflake metadata inspection and schema extraction."""
import logging
from typing import Any, Dict, List

import snowflake.connector  # pylint: disable=import-error,no-name-in-module

from scia.models.schema import ColumnSchema, TableSchema

logger = logging.getLogger(__name__)

class SnowflakeInspector:
    """Fetch schema metadata from Snowflake data warehouse."""

    def __init__(self, connection_params: Dict[str, Any]):
        """Initialize with connection parameters."""
        self.params = connection_params
        self.conn = None
    def connect(self):
        """Establish connection to Snowflake."""
        try:
            # pylint: disable=no-member
            self.conn = snowflake.connector.connect(**self.params)
        except snowflake.connector.errors.Error as e:  # pylint: disable=no-member
            logger.error("Failed to connect to Snowflake: %s", e)
            raise

    def fetch_schema(self, database: str, schema: str) -> List[TableSchema]:
        """Fetch metadata for all tables and views in a schema."""
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

            # Group columns by table
            tables_data: Dict[str, List[ColumnSchema]] = {}
            for row in cursor.fetchall():
                col = ColumnSchema(
                    schema_name=row[0],
                    table_name=row[1],
                    column_name=row[2],
                    data_type=row[3],
                    is_nullable=(row[4] == 'YES'),
                    ordinal_position=row[5]
                )
                if row[1] not in tables_data:
                    tables_data[row[1]] = []
                tables_data[row[1]].append(col)

            result = []
            for table_name, columns in tables_data.items():
                result.append(TableSchema(
                    schema_name=schema,
                    table_name=table_name,
                    columns=columns
                ))

            return result
        except snowflake.connector.errors.Error as e:
            logger.warning("Error fetching schema metadata: %s", e)
            return []

    def fetch_view_definitions(self, database: str,
                               schema: str) -> Dict[str, str]:
        """Fetch definitions for all views in a schema."""
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
        except snowflake.connector.errors.Error as e:
            logger.warning("Error fetching view definitions: %s", e)
            return {}

    def fetch_foreign_keys(self, database: str, schema: str) -> List[Dict[str, Any]]:
        """Fetch foreign key relationships (Stub for v0.2)."""
        # pylint: disable=unused-argument
        return []

    def close(self):
        """Close Snowflake connection."""
        if self.conn:
            self.conn.close()
