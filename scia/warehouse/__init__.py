"""Warehouse adapter registry and factory."""
import logging
from typing import Dict, Optional, Type

from scia.warehouse.base import WarehouseAdapter
from scia.warehouse.snowflake import SnowflakeAdapter

logger = logging.getLogger(__name__)


class WarehouseNotImplementedError(NotImplementedError):
    """Raised when a warehouse type is not yet implemented."""


class UnsupportedWarehouseError(ValueError):
    """Raised when an unsupported warehouse type is requested."""


# Registry of available warehouse adapters
# Format: warehouse_type -> adapter class (or None for stubs)
WAREHOUSE_ADAPTERS: Dict[str, Optional[Type[WarehouseAdapter]]] = {
    'snowflake': SnowflakeAdapter,
    'databricks': None,    # Stub: will be implemented in v0.2
    'postgres': None,      # Stub: will be implemented in v0.2
    'redshift': None,      # Stub: will be implemented in v0.2
}


def get_adapter(warehouse_type: str) -> WarehouseAdapter:
    """Get a warehouse adapter instance by type.

    Args:
        warehouse_type: Type of warehouse (snowflake, databricks, postgres, redshift)

    Returns:
        WarehouseAdapter instance for the specified warehouse

    Raises:
        UnsupportedWarehouseError: If warehouse type is not recognized
        WarehouseNotImplementedError: If warehouse type is stubbed (not implemented)
    """
    warehouse_type_lower = warehouse_type.lower()

    if warehouse_type_lower not in WAREHOUSE_ADAPTERS:
        raise UnsupportedWarehouseError(
            f"Unsupported warehouse: '{warehouse_type}'. "
            f"Supported types: {', '.join(WAREHOUSE_ADAPTERS.keys())}"
        )

    adapter_class = WAREHOUSE_ADAPTERS[warehouse_type_lower]

    if adapter_class is None:
        raise WarehouseNotImplementedError(
            f"Warehouse '{warehouse_type}' is not yet implemented. "
            f"Currently supported: snowflake"
        )

    logger.debug("Creating adapter for warehouse type: %s", warehouse_type_lower)
    return adapter_class()


def list_supported_warehouses() -> list[str]:
    """Get list of supported warehouse types.

    Returns:
        List of warehouse types that are fully implemented
    """
    return [
        wh_type for wh_type, adapter_class in WAREHOUSE_ADAPTERS.items()
        if adapter_class is not None
    ]


def list_planned_warehouses() -> list[str]:
    """Get list of planned (not yet implemented) warehouse types.

    Returns:
        List of warehouse types that are stubbed for future implementation
    """
    return [
        wh_type for wh_type, adapter_class in WAREHOUSE_ADAPTERS.items()
        if adapter_class is None
    ]
