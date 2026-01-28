"""Databricks warehouse adapter (stub for v0.2)."""
from typing import Any, Dict, List

from scia.models.schema import TableSchema
from scia.warehouse.base import WarehouseAdapter


class DatabricksAdapter(WarehouseAdapter):
    """Databricks warehouse adapter (placeholder for v0.2 implementation).
    
    This adapter will provide schema metadata fetching for Databricks Unity Catalog.
    Current status: Designed but not yet implemented.
    """

    def __init__(self):
        """Initialize Databricks adapter."""
        raise NotImplementedError(
            "Databricks adapter will be implemented in v0.2. "
            "Currently, only Snowflake is fully supported."
        )

    def connect(self, config: Dict[str, Any]) -> None:
        """Establish connection to Databricks workspace.
        
        Args:
            config: Databricks workspace configuration
            
        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Databricks adapter not yet implemented")

    def fetch_schema(self, database: str, schema: str) -> List[TableSchema]:
        """Fetch schema metadata for Databricks.
        
        Args:
            database: Catalog name
            schema: Schema name
            
        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Databricks adapter not yet implemented")

    def fetch_views(self, database: str, schema: str) -> Dict[str, str]:
        """Fetch view definitions from Databricks.
        
        Args:
            database: Catalog name
            schema: Schema name
            
        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Databricks adapter not yet implemented")

    def fetch_foreign_keys(self, database: str, schema: str) -> List[Dict[str, Any]]:
        """Fetch foreign key constraints from Databricks.
        
        Args:
            database: Catalog name
            schema: Schema name
            
        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Databricks adapter not yet implemented")

    def parse_table_references(self, sql: str) -> List[str]:
        """Parse SQL and extract table references.
        
        Args:
            sql: SQL statement
            
        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Databricks adapter not yet implemented")

    def close(self) -> None:
        """Close Databricks connection.
        
        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError("Databricks adapter not yet implemented")
