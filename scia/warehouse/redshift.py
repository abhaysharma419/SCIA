"""Amazon Redshift warehouse adapter (stub for v0.2)."""
from typing import Any, Dict, List

from scia.models.schema import TableSchema
from scia.warehouse.base import WarehouseAdapter


class RedshiftAdapter(WarehouseAdapter):
    """Amazon Redshift warehouse adapter (placeholder for v0.2 implementation).

    This adapter will provide schema metadata fetching for Redshift clusters.
    Current status: Designed but not yet implemented.
    """

    def __init__(self):
        """Initialize Redshift adapter."""
        raise NotImplementedError(
            "Redshift adapter will be implemented in v0.2. "
            "Currently, only Snowflake is fully supported."
        )

    def connect(self, config: Dict[str, Any]) -> None:
        """Establish connection to Redshift cluster.

        Args:
            config: Redshift cluster connection configuration

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Redshift adapter not yet implemented")

    def fetch_schema(self, database: str, schema: str) -> List[TableSchema]:
        """Fetch schema metadata for Redshift.

        Args:
            database: Database name
            schema: Schema name

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Redshift adapter not yet implemented")

    def fetch_views(self, database: str, schema: str) -> Dict[str, str]:
        """Fetch view definitions from Redshift.

        Args:
            database: Database name
            schema: Schema name

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Redshift adapter not yet implemented")

    def fetch_foreign_keys(self, database: str, schema: str) -> List[Dict[str, Any]]:
        """Fetch foreign key constraints from Redshift.

        Args:
            database: Database name
            schema: Schema name

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Redshift adapter not yet implemented")

    def parse_table_references(self, sql: str) -> List[str]:
        """Parse SQL and extract table references.

        Args:
            sql: SQL statement

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Redshift adapter not yet implemented")

    def close(self) -> None:
        """Close Redshift connection.

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Redshift adapter not yet implemented")
