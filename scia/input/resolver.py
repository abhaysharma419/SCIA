"""Input source detection and resolution."""
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class InputType(Enum):
    """Types of input sources for schema comparison."""

    JSON = "json"           # JSON schema files
    SQL = "sql"            # SQL DDL files
    DATABASE = "database"  # Live database (schema.table references)


class InputResolutionError(ValueError):
    """Raised when input resolution fails."""


def resolve_input(
    before: str,
    after: str,
    warehouse: Optional[str] = None
) -> Tuple[InputType, dict]:
    """Detect and resolve input sources for schema comparison.

    Supports three modes:
    1. JSON mode: Both before and after are JSON schema files
       - Paths: *.json files containing TableSchema definitions
    2. SQL mode: Before is JSON/DB, after is SQL migration file (or vice versa)
       - Paths: *.sql files containing DDL statements
    3. Database mode: Both are database references (SCHEMA.TABLE)
       - Format: database.schema or schema.table
       - Requires warehouse parameter for live schema fetch

    Args:
        before: Before input (file path or database reference)
        after: After input (file path or database reference)
        warehouse: Optional warehouse type (required for database mode)

    Returns:
        Tuple of (InputType, metadata_dict) containing:
        {
            'before_source': str (file path or db reference),
            'after_source': str (file path or db reference),
            'before_format': str (json|sql|database),
            'after_format': str (json|sql|database),
        }

    Raises:
        InputResolutionError: If input cannot be resolved or is ambiguous
    """
    # Detect input formats
    before_format = _detect_format(before)
    after_format = _detect_format(after)

    logger.debug("Detected before format: %s, after format: %s", before_format, after_format)

    # Determine overall input type
    if before_format == 'json' and after_format == 'json':
        input_type = InputType.JSON
    elif before_format == 'sql' or after_format == 'sql':
        input_type = InputType.SQL
    elif before_format == 'database' or after_format == 'database':
        if not warehouse:
            raise InputResolutionError(
                "Database mode requires --warehouse parameter. "
                "Example: scia analyze --before PROD.ANALYTICS --after DEV.ANALYTICS "
                "--warehouse snowflake"
            )
        input_type = InputType.DATABASE
    else:
        raise InputResolutionError(
            f"Unsupported input combination: {before_format} + {after_format}. "
            "Supported: json+json, json+sql, sql+sql, database+database"
        )

    # Validate input existence
    _validate_input_exists(before, before_format)
    _validate_input_exists(after, after_format)

    metadata = {
        'before_source': before,
        'after_source': after,
        'before_format': before_format,
        'after_format': after_format,
        'input_type': input_type.value,
    }

    if warehouse:
        metadata['warehouse'] = warehouse

    return input_type, metadata


def _detect_format(input_str: str) -> str:
    """Detect format of an input string.

    Args:
        input_str: Input string (file path or database reference)

    Returns:
        'json', 'sql', or 'database'
    """
    input_lower = input_str.lower()

    # Check for file extensions
    if input_lower.endswith('.json'):
        return 'json'
    if input_lower.endswith('.sql'):
        return 'sql'

    # Check for database references (SCHEMA.TABLE or DATABASE.SCHEMA.TABLE)
    if '.' in input_str and not input_str.startswith('.'):
        # Might be a database reference
        parts = input_str.split('.')
        if len(parts) in (2, 3):  # schema.table or database.schema.table
            # Verify parts look like identifiers (alphanumeric + underscore)
            if all(_is_valid_identifier(part) for part in parts):
                return 'database'

    # Check if it's a file path (with or without extension)
    if os.path.exists(input_str) or os.path.exists(input_str + '.json') or \
       os.path.exists(input_str + '.sql'):
        # It's a file, but we need extension to determine type
        if os.path.exists(input_str):
            path = Path(input_str)
            if path.suffix.lower() == '.json':
                return 'json'
            if path.suffix.lower() == '.sql':
                return 'sql'
        return 'json'  # Default to json if no extension and file exists

    # Default assumption: if not a file, assume database reference
    if '.' in input_str:
        return 'database'

    # Fallback: treat as file path
    return 'json'


def _is_valid_identifier(name: str) -> bool:
    """Check if string is a valid SQL identifier.

    Args:
        name: Identifier string

    Returns:
        True if valid identifier (alphanumeric + underscore)
    """
    if not name:
        return False

    # Remove quotes if present
    if (name.startswith('"') and name.endswith('"')) or \
       (name.startswith('`') and name.endswith('`')):
        name = name[1:-1]

    # Check if alphanumeric or underscore
    return name.replace('_', '').replace('-', '').isalnum()


def _validate_input_exists(input_str: str, input_format: str) -> None:
    """Validate that input exists or is valid.

    Args:
        input_str: Input string
        input_format: Detected format (json, sql, or database)

    Raises:
        InputResolutionError: If file doesn't exist or format is invalid
    """
    if input_format == 'database':
        # Database references don't need file validation
        return

    # Check if file exists
    if not os.path.exists(input_str):
        raise InputResolutionError(
            f"Input file not found: {input_str}"
        )
