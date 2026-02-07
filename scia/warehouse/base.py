"""Abstract base class for warehouse adapters."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from scia.models.schema import TableSchema


class WarehouseAdapter(ABC):
    """Abstract base class for warehouse-specific adapters.

    All warehouse implementations must inherit from this class and implement
    all abstract methods. This ensures consistent behavior across different
    warehouse platforms (Snowflake, Databricks, PostgreSQL, Redshift).
    """

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        """Establish connection to the warehouse.

        Args:
            config: Connection configuration dictionary with warehouse-specific parameters.
                For Snowflake: {account, user, password, warehouse, database, schema}
                For others: TBD in v0.2

        Raises:
            Exception: If connection fails (warehouse-specific exception)
        """

    @abstractmethod
    def fetch_schema(self, database: str, schema: str) -> List[TableSchema]:
        """Fetch schema metadata for all tables in a schema.

        Args:
            database: Database/catalog name
            schema: Schema name

        Returns:
            List of TableSchema objects with columns, or empty list if fetch fails.
            Never raises an exception; gracefully returns [] on failure.
        """

    @abstractmethod
    def fetch_views(self, database: str, schema: str) -> Dict[str, str]:
        """Fetch view definitions for all views in a schema.

        Args:
            database: Database/catalog name
            schema: Schema name

        Returns:
            Dictionary mapping view name to view definition SQL.
            Empty dict if fetch fails or no views found.
            Never raises an exception; gracefully returns {} on failure.
        """

    @abstractmethod
    def fetch_foreign_keys(self, database: str, schema: str) -> List[Dict[str, Any]]:
        """Fetch foreign key constraints for a schema.

        Args:
            database: Database/catalog name
            schema: Schema name

        Returns:
            List of foreign key definitions. Each dict contains:
            {
                'constraint_name': str,
                'table_name': str,
                'column_name': str,
                'referenced_table': str,
                'referenced_column': str
            }
            Empty list if no foreign keys found or fetch fails.
            Never raises an exception; gracefully returns [] on failure.
        """

    @abstractmethod
    def parse_table_references(self, sql: str) -> List[str]:
        """Parse SQL statement and extract table references.

        Args:
            sql: SQL statement text

        Returns:
            List of table names referenced in the SQL (schema.table format).
            Empty list if parsing fails or no tables found.
            Never raises an exception; gracefully returns [] on failure.
        """

    @abstractmethod
    def close(self) -> None:
        """Close the warehouse connection.

        Should be idempotent (safe to call multiple times).
        """
