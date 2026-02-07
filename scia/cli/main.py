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
        warehouse_type = getattr(args, 'warehouse', None)
        conn_file = getattr(args, 'conn_file', None)

        # 1. Resolve input sources
        input_type, metadata = resolve_input(args.before, args.after, warehouse_type)

        # 2. Get Warehouse Adapter
        warehouse_adapter = _get_warehouse_adapter(warehouse_type, conn_file)

        # 3. Load Schemas
        before_schema, after_schema, sql_definitions = _load_schemas(
            args, input_type, metadata, warehouse_adapter
        )

        # 4. Warnings and Analysis
        warnings = []
        if before_schema and after_schema:
            b_db = before_schema[0].database_name
            a_db = after_schema[0].database_name
            if b_db and a_db and b_db.upper() != a_db.upper():
                warnings.append(f"Database names are different: {b_db} vs {a_db}")

        # 5. Execute Analysis & Output
        analysis_config = {
            'dep_depth': getattr(args, 'dependency_depth', 3),
            'warnings': warnings,
            'include_up': getattr(args, 'include_upstream', True),
            'include_down': getattr(args, 'include_downstream', True),
            'output_format': getattr(args, 'format', 'json'),
            'fail_on': getattr(args, 'fail_on', 'HIGH')
        }

        await _execute_and_output(
            before_schema, after_schema, sql_definitions,
            warehouse_adapter, analysis_config
        )

        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if warehouse_adapter:
            warehouse_adapter.close()


async def _execute_and_output(
        before_schema, after_schema, sql_definitions,
        warehouse_adapter, config
):
    """Execute analysis and render output."""
    assessment = await analyze(
        before_schema,
        after_schema,
        sql_definitions=sql_definitions if sql_definitions else None,
        warehouse_adapter=warehouse_adapter if (
            config['include_up'] or config['include_down']
        ) else None,
        max_dependency_depth=config['dep_depth'],
        warnings=config['warnings']
    )

    if config['output_format'] == "json":
        print(render_json(assessment))
    else:
        print(render_markdown(assessment))

    _handle_exit_code(config['fail_on'], assessment.classification)


def _handle_exit_code(fail_on, classification):
    code = 0
    if fail_on == "HIGH" and classification == "HIGH":
        code = 1
    elif fail_on == "MEDIUM" and classification in ["HIGH", "MEDIUM"]:
        code = 1
    elif fail_on == "LOW" and classification in ["HIGH", "MEDIUM", "LOW"]:
        code = 1
    
    if code != 0:
        sys.exit(code)


def _get_warehouse_adapter(warehouse_type, conn_file):
    if not warehouse_type:
        return None
    try:
        config = load_connection_config(warehouse_type, conn_file)
        adapter = get_adapter(warehouse_type)
        adapter.connect(config)
        return adapter
    except Exception as e:  # pylint: disable=broad-except
        print(f"Warning: Failed to connect to {warehouse_type}: {e}", file=sys.stderr)
        return None


def _load_schemas(args, input_type, metadata, adapter):
    before_schema = []
    after_schema = []
    sql_definitions = {}

    if input_type == InputType.JSON:
        before_schema = load_schema_file(args.before)
        after_schema = load_schema_file(args.after)

    elif input_type == InputType.SQL:
        before_schema = _load_sql_before(args, metadata, adapter)
        after_schema, sql_definitions = _load_sql_after(
            args, metadata, adapter, before_schema
        )

    elif input_type == InputType.DATABASE:
        if not adapter:
            raise ValueError("Database mode requires --warehouse")
        before_schema = _fetch_schema_from_db(metadata['before_source'], adapter)
        after_schema = _fetch_schema_from_db(metadata['after_source'], adapter)

    return before_schema, after_schema, sql_definitions


def _load_sql_before(args, metadata, adapter):
    if metadata['before_format'] == 'sql':
        try:
            with open(args.before, 'r', encoding='utf-8') as f:
                return parse_ddl_to_schema(f.read())
        except Exception as e:  # pylint: disable=broad-except
            print(f"Warning: Failed to parse SQL in {args.before}: {e}", file=sys.stderr)
            return []
    elif metadata['before_format'] == 'database' and adapter:
        return _fetch_schema_from_db(args.before, adapter)
    return load_schema_file(args.before)


def _load_sql_after(args, metadata, adapter, before_schema):
    sql_defs = {}
    if metadata['after_format'] == 'sql':
        try:
            with open(args.after, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                schema = parse_ddl_to_schema(sql_content, base_schemas=before_schema)
                sql_defs = {"migration": sql_content}
                return schema, sql_defs
        except Exception as e:  # pylint: disable=broad-except
            print(f"Warning: Failed to parse SQL in {args.after}: {e}", file=sys.stderr)
            return before_schema, sql_defs
    elif metadata['after_format'] == 'database' and adapter:
        return _fetch_schema_from_db(args.after, adapter), sql_defs
    return load_schema_file(args.after), sql_defs

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
