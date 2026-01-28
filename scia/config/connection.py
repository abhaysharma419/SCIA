"""Connection configuration management."""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class ConnectionConfigError(ValueError):
    """Raised when connection configuration loading fails."""


def load_connection_config(
    conn_file: Optional[str] = None,
    warehouse: Optional[str] = None
) -> Dict[str, Any]:
    """Load warehouse connection configuration.

    Loads configuration with the following priority:
    1. Explicit --conn-file path (highest priority)
    2. ~/.scia/{warehouse}.yaml
    3. Sensible defaults if none provided

    Args:
        warehouse: Warehouse type (snowflake, databricks, postgres, redshift)
        conn_file: Optional explicit connection file path

    Returns:
        Dictionary with connection configuration

    Raises:
        ConnectionConfigError: If configuration file is invalid
    """
    config = {}

    # Try explicit file first
    if conn_file:
        config = _load_yaml_config(conn_file, warehouse)
        logger.info("Loaded connection config from: %s", conn_file)
        return config

    # Try default location
    default_path = Path.home() / '.scia' / f'{warehouse.lower()}.yaml'
    if default_path.exists():
        config = _load_yaml_config(str(default_path), warehouse)
        logger.info("Loaded connection config from: %s", default_path)
        return config

    # Try environment variables
    env_config = _load_from_env(warehouse)
    if env_config:
        logger.info("Loaded connection config from environment variables")
        return env_config

    # Return empty config (will likely fail at connection time)
    logger.warning("No connection config found for %s. Using defaults.", warehouse)
    return _get_defaults(warehouse)


def _load_yaml_config(file_path: str, warehouse: str) -> Dict[str, Any]:
    """Load YAML configuration file.

    Args:
        file_path: Path to YAML config file
        warehouse: Warehouse type (for validation)

    Returns:
        Parsed configuration dictionary

    Raises:
        ConnectionConfigError: If file is invalid or missing
    """
    try:
        if not os.path.exists(file_path):
            raise ConnectionConfigError(f"Configuration file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ConnectionConfigError(
                f"Configuration file must contain a YAML dictionary: {file_path}"
            )

        return config

    except yaml.YAMLError as e:
        raise ConnectionConfigError(
            f"Invalid YAML configuration: {file_path}\n{e}"
        ) from e
    except OSError as e:
        raise ConnectionConfigError(
            f"Error reading configuration file: {file_path}\n{e}"
        ) from e


def _load_from_env(warehouse: str) -> Optional[Dict[str, Any]]:
    """Load configuration from environment variables.

    Looks for warehouse-specific env vars (e.g., SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER).

    Args:
        warehouse: Warehouse type

    Returns:
        Configuration dictionary or None if no env vars found
    """
    prefix = warehouse.upper()
    config = {}

    # Common connection parameters
    common_params = ['ACCOUNT', 'USER', 'PASSWORD', 'HOST', 'PORT', 'DATABASE']

    for param in common_params:
        env_key = f"{prefix}_{param}"
        value = os.getenv(env_key)
        if value:
            config[param.lower()] = value

    return config if config else None


def _get_defaults(warehouse: str) -> Dict[str, Any]:
    """Get default configuration for a warehouse.

    Args:
        warehouse: Warehouse type

    Returns:
        Default configuration dictionary
    """
    warehouse_lower = warehouse.lower()

    if warehouse_lower == 'snowflake':
        return {
            'account': '',
            'user': '',
            'password': '',
            'warehouse': 'COMPUTE_WH',
            'database': '',
            'schema': 'PUBLIC'
        }

    if warehouse_lower == 'postgres':
        return {
            'host': 'localhost',
            'port': 5432,
            'user': '',
            'password': '',
            'database': ''
        }

    if warehouse_lower == 'databricks':
        return {
            'host': '',
            'token': '',
            'catalog': 'hive_metastore',
        }

    if warehouse_lower == 'redshift':
        return {
            'host': '',
            'port': 5439,
            'user': '',
            'password': '',
            'database': ''
        }

    return {}


def validate_connection_config(
    warehouse: str,
    config: Dict[str, Any]
) -> bool:
    """Validate that required connection parameters are present.

    Args:
        warehouse: Warehouse type
        config: Configuration dictionary

    Returns:
        True if configuration has required parameters

    Raises:
        ConnectionConfigError: If required parameters are missing
    """
    warehouse_lower = warehouse.lower()
    required_fields = []

    if warehouse_lower == 'snowflake':
        required_fields = ['account', 'user', 'password']

    elif warehouse_lower == 'postgres':
        required_fields = ['host', 'user', 'password', 'database']

    elif warehouse_lower == 'databricks':
        required_fields = ['host', 'token']

    elif warehouse_lower == 'redshift':
        required_fields = ['host', 'user', 'password', 'database']

    missing_fields = [f for f in required_fields if f not in config or not config[f]]

    if missing_fields:
        raise ConnectionConfigError(
            f"Missing required connection parameters for {warehouse}: "
            f"{', '.join(missing_fields)}. "
            f"Provide via --conn-file or ~/.scia/{warehouse.lower()}.yaml"
        )

    return True
