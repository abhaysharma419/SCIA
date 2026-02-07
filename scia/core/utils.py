"""Core utility functions for SCIA."""
from typing import Tuple

def parse_identifier(identifier: str) -> Tuple[str, str, str]:
    """Parse a database identifier into (database, schema, table).

    Supports:
    - TABLE
    - SCHEMA.TABLE
    - DATABASE.SCHEMA.TABLE

    Returns:
        Tuple of (database, schema, table). Empty strings if not present.
    """
    if not identifier:
        return "", "", ""

    parts = identifier.split('.')
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return "", parts[0], parts[1]
    return "", "", identifier
