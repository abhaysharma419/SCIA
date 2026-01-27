# SCIA Project Folder Structure

## Recommended Directory Layout

```
SCIA/
├── .github/
│   ├── workflows/           # CI/CD workflows (GitHub Actions)
│   │   ├── tests.yml
│   │   ├── lint.yml
│   │   └── publish.yml
│   ├── copilot-instructions.md  # AI agent guidance (authoritative)
│   └── ISSUE_TEMPLATE/      # GitHub issue templates
│
├── docs/                    # Documentation (locked v0.1 decisions)
│   ├── design.md           # Architecture & locked decisions (v0.1)
│   ├── REQUIREMENTS.md      # Functional spec (locked v0.1)
│   ├── API.md              # API reference (optional)
│   └── examples/           # Usage examples
│       ├── before.json
│       ├── after.json
│       └── output_example.json
│
├── scia/                    # Main package
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py         # Command-line interface
│   ├── core/
│   │   ├── __init__.py
│   │   ├── analyze.py      # Orchestration pipeline
│   │   ├── diff.py         # Schema diffing logic
│   │   ├── rules.py        # Deterministic rules engine
│   │   └── risk.py         # Risk aggregation & classification
│   ├── metadata/
│   │   ├── __init__.py
│   │   └── snowflake.py    # Snowflake metadata inspector
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schema.py       # TableSchema, ColumnSchema
│   │   └── finding.py      # Finding, FindingType, Severity
│   ├── output/
│   │   ├── __init__.py
│   │   ├── json.py         # JSON renderer (primary)
│   │   └── markdown.py     # Markdown renderer (optional)
│   └── sql/
│       ├── __init__.py
│       ├── parser.py       # SQL parsing (best-effort)
│       └── heuristics.py   # SQL signal extraction
│
├── tests/                   # Unit & integration tests
│   ├── __init__.py
│   ├── test_diff.py        # Schema diff tests
│   ├── test_rules.py       # Rule application tests
│   ├── test_risk.py        # Risk aggregation tests
│   ├── test_cli.py         # CLI integration tests
│   ├── test_output.py      # Output renderer tests
│   └── fixtures/           # Test data
│       ├── before_schema.json
│       ├── after_schema.json
│       └── expected_findings.json
│
├── pyproject.toml          # Package metadata, dependencies, build config
├── README.md               # Project overview & quick start
├── .gitignore             # Git ignore rules
├── LICENSE                # License (MIT/Apache)
└── CHANGELOG.md           # Version history & release notes
```

## File Organization Rationale

### `/docs/` — Locked Documentation
- **design.md**: Architecture decisions (v0.1 frozen)
- **REQUIREMENTS.md**: Functional spec (v0.1 frozen)
- Kept separate from code to emphasize "read-only" status
- Avoid committing to root directory clutter

### `/tests/` — Comprehensive Testing
- Mirrors source structure for clarity
- `fixtures/` subdirectory for test data (JSON schemas)
- Each module has corresponding `test_*.py` file
- Include integration tests for CLI, end-to-end flows

### `/scia/` — Package Structure
- Clear module separation by responsibility
- No circular imports (data models → diff → rules → risk → output)
- `__init__.py` in each subdirectory for clean imports

### `.github/` — Project Configuration
- `.github/copilot-instructions.md` → AI agent guidance (not in docs/)
- `workflows/` → CI/CD pipelines
- GitHub-specific configuration kept isolated

## Import Paths (Clean Namespace)

After installation (`pip install -e .`):

```python
# Data models
from scia.models.schema import TableSchema, ColumnSchema
from scia.models.finding import Finding, FindingType, Severity

# Core pipeline
from scia.core.diff import diff_schemas, SchemaDiff
from scia.core.rules import apply_rules
from scia.core.risk import RiskAssessment
from scia.core.analyze import analyze

# Output
from scia.output.json import render_json
from scia.output.markdown import render_markdown

# SQL utilities
from scia.sql.parser import parse_sql
from scia.sql.heuristics import extract_signals

# Metadata sources
from scia.metadata.snowflake import SnowflakeInspector

# CLI
from scia.cli.main import main
```

## Testing Strategy

```
tests/
├── test_diff.py           # Unit: Diff detection
├── test_rules.py          # Unit: Rule application
├── test_risk.py           # Unit: Risk scoring & classification
├── test_output.py         # Unit: JSON/Markdown rendering
├── test_cli.py            # Integration: CLI commands & exit codes
├── fixtures/
│   ├── before_schema.json # Sample: Column removal case
│   ├── after_schema.json
│   └── expected_findings.json
```

Run tests with:
```bash
pytest tests/                 # All tests
pytest tests/test_diff.py    # Specific module
pytest -v --cov             # With coverage report
```

## Do NOT Add

- Top-level `config/`, `scripts/`, `migrations/` folders
- Package-internal folders under `/scia/` (no `/scia/utils/`, etc.)
- Multiple docs directories (keep all in `/docs/`)
- Example files in root (use `/docs/examples/`)

## Future Extensions (v0.2+)

If expanding beyond v0.1, add folders at package level:

```
scia/
├── metadata/snowflake.py   # v0.1
├── metadata/bigquery.py    # v0.2: BigQuery support
├── metadata/databricks.py  # v0.2: Databricks support
│
├── sql/
│   ├── parser.py
│   ├── dialects/          # v0.2: Multiple SQL dialects
│   │   ├── snowflake.py
│   │   ├── bigquery.py
│   │   └── postgres.py
```

But do NOT create these until v0.2 is planned — maintain simplicity.
