"""Snowflake warehouse adapter implementation."""
import logging
from typing import Any, Dict, List

import snowflake.connector  # pylint: disable=import-error,no-name-in-module

from scia.models.schema import ColumnSchema, TableSchema
from scia.warehouse.base import WarehouseAdapter

logger = logging.getLogger(__name__)


class SnowflakeAdapter(WarehouseAdapter):
    """Snowflake warehouse adapter for fetching metadata and analyzing schemas."""

    def __init__(self):
        """Initialize Snowflake adapter."""
        self.conn = None

    def _resolve_context(self, cursor, database: str, schema: str):
        """Resolve database and schema names.
        
        If not provided, fetch current context from session.
        """
        target_database = database
        target_schema = schema.upper() if schema else ""

        if not target_database or not target_schema:
            cursor.execute("SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()")
            default_db, default_schema = cursor.fetchone()
            target_database = target_database or default_db
            target_schema = target_schema or (default_schema if default_schema else "PUBLIC")
        
        return target_database, target_schema

    def connect(self, config: Dict[str, Any]) -> None:
        """Establish connection to Snowflake warehouse.

        Args:
            config: Connection configuration with keys:
                - account: Snowflake account identifier
                - user: Username
                - password: Password
                - warehouse: Warehouse name (optional)
                - database: Database name (optional)
                - schema: Schema name (optional)

        Raises:
            snowflake.connector.errors.Error: If connection fails
        """
        try:
            self.conn = snowflake.connector.connect(**config)
            logger.info("Successfully connected to Snowflake")
        except snowflake.connector.errors.Error as e:  # pylint: disable=no-member
            logger.error("Failed to connect to Snowflake: %s", e)
            raise

    def fetch_schema(self, database: str, schema: str) -> List[TableSchema]:
        """Fetch schema metadata for all tables in a Snowflake schema.

        Args:
            database: Database name
            schema: Schema name

        Returns:
            List of TableSchema objects with columns. Empty list on failure.
        """
        if not self.conn:
            logger.warning("Not connected to Snowflake. Call connect() first.")
            return []

        try:
            cursor = self.conn.cursor()

            # Resolve database and schema names
            target_database, target_schema = self._resolve_context(cursor, database, schema)
            
            if not target_database:
                logger.warning("No database specified or found for schema fetch.")
                return []

            from_clause = f"{target_database}.INFORMATION_SCHEMA.COLUMNS"

            # Fetch columns metadata from INFORMATION_SCHEMA
            query = f"""
            SELECT
                TABLE_SCHEMA,
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                ORDINAL_POSITION
            FROM {from_clause}
            WHERE TABLE_SCHEMA = '{target_schema}'
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

            # Convert to TableSchema objects
            result = []
            for table_name, columns in tables_data.items():
                result.append(TableSchema(
                    schema_name=target_schema,
                    table_name=table_name,
                    columns=columns
                ))

            logger.info("Fetched %d tables from %s.%s", len(result), database, schema)
            return result

        except snowflake.connector.errors.Error as e:  # pylint: disable=no-member
            logger.warning("Error fetching schema metadata: %s", e)
            return []

    def fetch_views(self, database: str, schema: str) -> Dict[str, str]:
        """Fetch view definitions for all views in a Snowflake schema.

        Args:
            database: Database name
            schema: Schema name

        Returns:
            Dictionary mapping view name to view definition SQL.
            Empty dict on failure or if no views found.
        """
        if not self.conn:
            logger.warning("Not connected to Snowflake. Call connect() first.")
            return {}

        try:
            cursor = self.conn.cursor()
            
            # Resolve database and schema names
            target_database, target_schema = self._resolve_context(cursor, database, schema)
            
            if not target_database:
                logger.warning("No database specified or found for views fetch.")
                return {}

            from_clause = f"{target_database}.INFORMATION_SCHEMA.VIEWS"

            query = f"""
            SELECT TABLE_NAME, VIEW_DEFINITION
            FROM {from_clause}
            WHERE TABLE_SCHEMA = '{target_schema}'
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            result = {row[0]: row[1] for row in rows if row[1]}
            logger.info("Fetched %d views from %s.%s", len(result), database, schema)
            return result

        except snowflake.connector.errors.Error as e:  # pylint: disable=no-member
            logger.warning("Error fetching view definitions: %s", e)
            return {}

    def fetch_foreign_keys(self, database: str, schema: str) -> List[Dict[str, Any]]:
        """Fetch foreign key constraints for a Snowflake schema.

        Args:
            database: Database name
            schema: Schema name

        Returns:
            List of foreign key definitions. Empty list on failure.
        """
        if not self.conn:
            logger.warning("Not connected to Snowflake. Call connect() first.")
            return []

        try:
            cursor = self.conn.cursor()
            
            # Resolve database and schema names
            target_database, target_schema = self._resolve_context(cursor, database, schema)

            if not target_database:
                logger.warning("No database specified or found for foreign key fetch.")
                return []
            
            # In Snowflake, SHOW IMPORTED KEYS IN SCHEMA <db>.<schema> is the most reliable way 
            # to get foreign keys with their respective columns.
            query = f"SHOW IMPORTED KEYS IN SCHEMA {target_database}.{target_schema}"

            logger.debug("Executing foreign key query: %s", query)
            cursor.execute(query)
            
            # Fetch all rows and map them to the expected format
            # Column indices for SHOW IMPORTED KEYS:
            # 2: pk_table_name, 3: pk_column_name, 6: fk_table_name, 7: fk_column_name, 11: fk_name
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    'constraint_name': row[11],
                    'table_name': row[6],
                    'column_name': row[7],
                    'referenced_table': row[2],
                    'referenced_column': row[3]
                })

            logger.info("Fetched %d foreign keys from %s.%s", len(result), database, schema)
            return result

        except snowflake.connector.errors.Error as e:  # pylint: disable=no-member
            logger.warning("Error fetching foreign keys: %s", e)
            return []

    def parse_table_references(self, sql: str) -> List[str]:
        """Parse SQL statement and extract table references.

        Uses sqlglot to parse SQL in Snowflake dialect.

        Args:
            sql: SQL statement text

        Returns:
            List of table names referenced (schema.table format).
            Empty list on parse failure.
        """
        try:
            from scia.sql.parser import extract_table_references
            tables = extract_table_references(sql, dialect='snowflake')
            logger.debug("Extracted %d table references from SQL", len(tables))
            return tables
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("Error parsing table references: %s", e)
            return []

    def close(self) -> None:
        """Close Snowflake connection."""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Closed Snowflake connection")
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("Error closing connection: %s", e)
            finally:
                self.conn = None
