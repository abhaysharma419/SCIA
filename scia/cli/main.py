"""Command-line interface for SCIA - SQL Change Impact Analyzer."""
import argparse
import asyncio
import json  # pylint: disable=import-self
import logging
import sys
from typing import List

from scia.config.connection import load_connection_config
from scia.core.analyze import analyze
from scia.core.utils import parse_identifier
from scia.input.resolver import InputType, resolve_input
from scia.models.schema import TableSchema
from scia.output.json import render_json
from scia.output.markdown import render_markdown
from scia.sql.ddl_parser import parse_ddl_to_schema
from scia.warehouse import get_adapter

logger = logging.getLogger(__name__)

def load_schema_file(path: str) -> List[TableSchema]:
    """Internal helper to load schema from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, list):
            return [TableSchema(**t) for t in data]
        return [TableSchema(**data)]

def _fetch_schema_from_db(identifier: str, adapter) -> List[TableSchema]:
    """Internal helper to fetch schema from database identifier."""
    database, schema, table = parse_identifier(identifier)
    
    # Ambiguity treatment: If 2 parts were provided (schema, table) but we want a WHOLE schema,
    # then parts are more likely to be (database, schema).
    if not database and schema and table:
        database = schema
        schema = table
        
    return adapter.fetch_schema(database, schema)

async def run_analyze(args):
    """Async execution wrapper for analyze command."""
    warehouse_adapter = None
    try:
        # Resolve optional arguments that might be missing in diff command
        warehouse_type = getattr(args, 'warehouse', None)
        conn_file = getattr(args, 'conn_file', None) # Corrected from 'conn-file'
        dep_depth = getattr(args, 'dependency_depth', 3) # Corrected from 'dependency-depth'
        include_up = getattr(args, 'include_upstream', True)
        include_down = getattr(args, 'include_downstream', True)
        output_format = getattr(args, 'format', 'json')
        fail_on = getattr(args, 'fail_on', 'HIGH')

        # 1. Resolve input sources
        input_type, metadata = resolve_input(args.before, args.after, warehouse_type)
        
        # 2. Initialize warehouse adapter if needed
        if warehouse_type:
            config = load_connection_config(warehouse_type, conn_file)
            warehouse_adapter = get_adapter(warehouse_type)
            warehouse_adapter.connect(config)

        before_schema = []
        after_schema = []
        sql_definitions = {}

        # 3. Load schemas and SQL signals based on input type
        if input_type == InputType.JSON:
            before_schema = load_schema_file(args.before)
            after_schema = load_schema_file(args.after)
        
        elif input_type == InputType.SQL:
            # Handle Before
            if metadata['before_format'] == 'sql':
                with open(args.before, 'r', encoding='utf-8') as f:
                    before_schema = parse_ddl_to_schema(f.read())
            elif metadata['before_format'] == 'database' and warehouse_adapter:
                before_schema = _fetch_schema_from_db(args.before, warehouse_adapter)
            else:
                before_schema = load_schema_file(args.before)
                
            # Handle After
            if metadata['after_format'] == 'sql':
                with open(args.after, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                    after_schema = parse_ddl_to_schema(sql_content)
                    sql_definitions = {"migration": sql_content}
            elif metadata['after_format'] == 'database' and warehouse_adapter:
                after_schema = _fetch_schema_from_db(args.after, warehouse_adapter)
            else:
                after_schema = load_schema_file(args.after)

        elif input_type == InputType.DATABASE:
            if not warehouse_adapter:
                # Should have been caught by resolve_input, but being safe
                raise ValueError("Database mode requires --warehouse")
            before_schema = _fetch_schema_from_db(metadata['before_source'], warehouse_adapter)
            after_schema = _fetch_schema_from_db(metadata['after_source'], warehouse_adapter)

        # 4. Execute Analysis
        assessment = await analyze(
            before_schema,
            after_schema,
            sql_definitions=sql_definitions if sql_definitions else None,
            warehouse_adapter=warehouse_adapter if (
                include_up or include_down
            ) else None,
            max_dependency_depth=dep_depth
        )

        # 5. Output results
        if output_format == "json":
            print(render_json(assessment))
        else:
            print(render_markdown(assessment))

        # 6. Exit code logic
        if fail_on == "HIGH" and assessment.classification == "HIGH":
            sys.exit(1)
        if fail_on == "MEDIUM" and assessment.classification in ["HIGH", "MEDIUM"]:
            sys.exit(1)
        if fail_on == "LOW" and assessment.classification in ["HIGH", "MEDIUM", "LOW"]:
            sys.exit(1)

        sys.exit(0)

    except Exception as e: # pylint: disable=broad-except
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if warehouse_adapter:
            warehouse_adapter.close()

def main():
    """Parse command line arguments and execute appropriate command."""
    parser = argparse.ArgumentParser(description="SCIA - SQL Change Impact Analyzer")
    subparsers = parser.add_subparsers(dest="command")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument(
        "--before", required=True,
        help="Before schema (JSON file, SQL file, or SCHEMA.TABLE)"
    )
    analyze_parser.add_argument(
        "--after", required=True,
        help="After schema (JSON file, SQL file, or SCHEMA.TABLE)"
    )
    analyze_parser.add_argument(
        "--warehouse",
        choices=["snowflake", "databricks", "postgres", "redshift"],
        help="Warehouse type"
    )
    analyze_parser.add_argument("--conn-file", help="Path to connection config file")
    analyze_parser.add_argument(
        "--dependency-depth", type=int, default=3,
        help="Max depth for dependency analysis (1-10)"
    )
    analyze_parser.add_argument(
        "--include-upstream", action="store_true", default=True,
        help="Include upstream dependencies"
    )
    analyze_parser.add_argument(
        "--no-upstream", action="store_false", dest="include_upstream"
    )
    analyze_parser.add_argument(
        "--include-downstream", action="store_true", default=True,
        help="Include downstream dependencies"
    )
    analyze_parser.add_argument(
        "--no-downstream", action="store_false", dest="include_downstream"
    )
    analyze_parser.add_argument(
        "--format", choices=["json", "markdown"], default="json"
    )
    analyze_parser.add_argument(
        "--fail-on", choices=["HIGH", "MEDIUM", "LOW"], default="HIGH"
    )

    # Diff command (legacy/simple)
    diff_parser = subparsers.add_parser("diff")
    diff_parser.add_argument("--before", required=True)
    diff_parser.add_argument("--after", required=True)

    args = parser.parse_args()

    if args.command == "analyze":
        asyncio.run(run_analyze(args))
    elif args.command == "diff":
        # Simplified for backward compatibility
        asyncio.run(run_analyze(args))
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
