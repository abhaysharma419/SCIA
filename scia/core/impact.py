"""Downstream and upstream impact analysis."""
import logging
from typing import Dict, List, Optional

from scia.core.utils import parse_identifier
from scia.models.finding import DependencyObject
from scia.warehouse.base import WarehouseAdapter

logger = logging.getLogger(__name__)

async def analyze_downstream(
    changed_table: str,
    warehouse_adapter: WarehouseAdapter,
    max_depth: int = 3
) -> List[DependencyObject]:
    """Recursively find views/tables depending on changed_table.
    
    Args:
        changed_table: Fully qualified table name (DATABASE.SCHEMA.TABLE)
        warehouse_adapter: Adapter to query warehouse metadata
        max_depth: Maximum recursion depth for transitive dependencies
        
    Returns:
        List of DependencyObject representing downstream dependents.
    """
    # Get database and schema from fully qualified table name
    database, schema, _ = parse_identifier(changed_table)

    all_dependents = []
    processed_objects = {changed_table.upper()}
    # Queue stores (object_name, current_depth)
    queue = [(changed_table.upper(), 0)]

    try:
        # Fetch all views in the schema once to avoid repeated network calls
        views = warehouse_adapter.fetch_views(database, schema)
    except Exception as e: # pylint: disable=broad-except
        logger.warning("Failed to fetch views for impact analysis: %s", e)
        return []

    while queue:
        current_obj, depth = queue.pop(0)
        if depth >= max_depth:
            continue

        for view_name, sql in views.items():
            # Build fully qualified view name for tracking
            if database and schema:
                full_view_name = f"{database}.{schema}.{view_name}".upper()
            elif schema:
                full_view_name = f"{schema}.{view_name}".upper()
            else:
                full_view_name = view_name.upper()

            if full_view_name in processed_objects:
                continue

            ref_tables = warehouse_adapter.parse_table_references(sql)
            # Normalize references for comparison
            normalized_refs = [t.upper() for t in ref_tables]
            
            # Use both short and long names for matching to be robust
            target_matches = {current_obj}
            if '.' in current_obj:
                target_matches.add(current_obj.split('.')[-1])

            if any(ref in target_matches for ref in normalized_refs):
                dep_obj = DependencyObject(
                    object_type="VIEW",
                    name=view_name,
                    schema=schema,
                    is_critical=False
                )
                all_dependents.append(dep_obj)
                processed_objects.add(full_view_name)
                queue.append((full_view_name, depth + 1))

    return all_dependents

async def analyze_upstream(
    changed_table: str,
    warehouse_adapter: WarehouseAdapter
) -> List[DependencyObject]:
    """Find tables/views this table depends on (e.g., via Foreign Keys).
    
    Args:
        changed_table: Fully qualified table name
        warehouse_adapter: Adapter to query warehouse metadata
        
    Returns:
        List of DependencyObject representing upstream dependencies.
    """
    database, schema, table_name = parse_identifier(changed_table)
    if not table_name:
        return []

    table_name = table_name.upper()

    all_upstream = []
    try:
        fks = warehouse_adapter.fetch_foreign_keys(database, schema)
        for fk in fks:
            if fk.get('table_name', '').upper() == table_name:
                dep_obj = DependencyObject(
                    object_type="TABLE",
                    name=fk.get('referenced_table', ''),
                    schema=schema, # Assuming same schema if not specified
                    is_critical=True # Foreign keys indicate tight coupling
                )
                all_upstream.append(dep_obj)
    except Exception as e: # pylint: disable=broad-except
        logger.warning("Failed to fetch foreign keys for upstream analysis: %s", e)

    return all_upstream
