"""PostgreSQL warehouse adapter (stub for v0.2)."""
from typing import Any, Dict, List

from scia.models.schema import TableSchema
from scia.warehouse.base import WarehouseAdapter


class PostgresAdapter(WarehouseAdapter):
    """PostgreSQL warehouse adapter (placeholder for v0.2 implementation).

    This adapter will provide schema metadata fetching for PostgreSQL databases.
    Current status: Designed but not yet implemented.
    """

    def __init__(self):
        """Initialize PostgreSQL adapter."""
        raise NotImplementedError(
            "PostgreSQL adapter will be implemented in v0.2. "
            "Currently, only Snowflake is fully supported."
        )

    def connect(self, config: Dict[str, Any]) -> None:
        """Establish connection to PostgreSQL database.

        Args:
            config: PostgreSQL connection configuration

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("PostgreSQL adapter not yet implemented")

    def fetch_schema(self, database: str, schema: str) -> List[TableSchema]:
        """Fetch schema metadata for PostgreSQL.

        Args:
            database: Database name
            schema: Schema name

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("PostgreSQL adapter not yet implemented")

    def fetch_views(self, database: str, schema: str) -> Dict[str, str]:
        """Fetch view definitions from PostgreSQL.

        Args:
            database: Database name
            schema: Schema name

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("PostgreSQL adapter not yet implemented")

    def fetch_foreign_keys(self, database: str, schema: str) -> List[Dict[str, Any]]:
        """Fetch foreign key constraints from PostgreSQL.

        Args:
            database: Database name
            schema: Schema name

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("PostgreSQL adapter not yet implemented")

    def parse_table_references(self, sql: str) -> List[str]:
        """Parse SQL and extract table references.

        Args:
            sql: SQL statement

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("PostgreSQL adapter not yet implemented")

    def close(self) -> None:
        """Close PostgreSQL connection.

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("PostgreSQL adapter not yet implemented")
