"""Command-line interface for SCIA - SQL Change Impact Analyzer."""
import argparse
import json  # pylint: disable=import-self
import sys
from scia.core.analyze import analyze
from scia.models.schema import TableSchema
from scia.output.json import render_json
from scia.output.markdown import render_markdown

def load_schema_file(path: str) -> list[TableSchema]:
    """Load and parse schema from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, list):
            return [TableSchema(**t) for t in data]
        return [TableSchema(**data)]

def main():
    """Parse command line arguments and execute appropriate command."""
    parser = argparse.ArgumentParser(description="SCIA - SQL Change Impact Analyzer")
    subparsers = parser.add_subparsers(dest="command")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("--before", required=True, help="Path to before_schema.json")
    analyze_parser.add_argument("--after", required=True, help="Path to after_schema.json")
    analyze_parser.add_argument("--format", choices=["json", "markdown"], default="json")
    analyze_parser.add_argument("--fail-on", choices=["HIGH", "MEDIUM", "LOW"], default="HIGH")

    # Diff command (simpler version of analyze)
    diff_parser = subparsers.add_parser("diff")
    diff_parser.add_argument("--before", required=True)
    diff_parser.add_argument("--after", required=True)

    args = parser.parse_args()

    if args.command == "analyze":
        try:
            before = load_schema_file(args.before)
            after = load_schema_file(args.after)

            assessment = analyze(before, after)

            if args.format == "json":
                print(render_json(assessment))
            else:
                print(render_markdown(assessment))

            # Exit code logic
            if args.fail_on == "HIGH" and assessment.classification == "HIGH":
                sys.exit(1)
            if args.fail_on == "MEDIUM" and assessment.classification in ["HIGH", "MEDIUM"]:
                sys.exit(1)
            if args.fail_on == "LOW" and assessment.classification in ["HIGH", "MEDIUM", "LOW"]:
                sys.exit(1)

            sys.exit(0)
        except FileNotFoundError as e:
            print(f"Error: File not found - {e}", file=sys.stderr)
            sys.exit(1)
        except (ValueError, TypeError) as e:
            print(f"Error: Invalid input - {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "diff":
        # Simplified output for diff command if needed
        before = load_schema_file(args.before)
        after = load_schema_file(args.after)
        assessment = analyze(before, after)
        print(render_json(assessment))
        sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
