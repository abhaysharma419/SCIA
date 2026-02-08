# SCIA Development Guide for AI Agents

This guide helps AI agents understand SCIA's architecture, patterns, and development workflow.

## Project Overview

**SCIA (Schema Change Impact Analyzer)** is a deterministic SQL-first risk assessment tool for schema changes. It operates as a linear pipeline: Input → Schema Diff → Rule Engine → Risk Aggregator → Output.

## Build & Test Commands

```bash
# Install dependencies
pip install -e .

# Run all tests
pytest

# Run single test file
pytest tests/test_diff.py

# Run specific test
pytest tests/test_diff.py::test_schema_diff_no_changes

# Run with coverage
pytest --cov=scia

# Run linting (if available)
# Note: No explicit lint command found in pyproject.toml
```

## Code Style Guidelines

### 1. Data Models (Pydantic BaseModel)

All data structures use Pydantic BaseModel in `models/`:
- **ColumnSchema**: Required fields - `schema_name`, `table_name`, `column_name`, `data_type`, `is_nullable`, `ordinal_position`
- **TableSchema**: Container for `List[ColumnSchema]`
- **Finding**: Risk finding with `finding_type`, `severity`, `base_risk`, `evidence`, `description`
- **SchemaDiff**: Container for detected changes

All models are immutable and validated on construction. Never mutate after creation.

### 2. Import Conventions

```python
# Standard library first
from typing import List, Optional, Dict, Any
from enum import Enum

# Third-party imports
from pydantic import BaseModel, Field, ConfigDict

# Local imports - use absolute imports
from scia.models.schema import ColumnSchema, TableSchema
from scia.models.finding import Finding, FindingType, Severity
from scia.core.diff import SchemaDiff
from scia.core.rules import apply_rules
```

### 3. Rule Application Pattern

Rules follow strict function pattern in `core/rules.py`:

```python
def rule_column_removed(diff: SchemaDiff) -> List[Finding]:
    """Each rule inspects diff and emits findings."""
    findings = []
    for change in diff.changes:
        if change.change_type == 'REMOVED' and change.object_type == 'COLUMN':
            findings.append(Finding(
                finding_type=FindingType.COLUMN_REMOVED,
                severity=Severity.HIGH,
                base_risk=80,
                evidence={"schema": change.schema_name, "table": change.table_name, "column": change.column_name},
                description=f"Column '{change.column_name}' removed from table '{change.table_name}'"
            ))
    return findings
```

**Rules MUST NOT:**
- Return early on first match (aggregate all findings)
- Modify diff in-place
- Make assumptions about missing signals
- Use floating-point risk scores (use integer base_risk)

### 4. Error Handling & Graceful Degradation

Missing signals should omit findings, not crash:
- SQL parsing failures → skip SQL-based findings
- Missing metadata → skip usage-based findings
- No query history → skip adoption-based scoring

SCIA never guesses. If you can't verify it, don't report it.

### 5. Naming Conventions

- **Functions**: snake_case with descriptive names (`rule_column_removed`, `diff_schemas`)
- **Classes**: PascalCase for Pydantic models (`ColumnSchema`, `Finding`)
- **Constants**: UPPER_SNAKE_CASE (`ALL_RULES`, `FindingType`)
- **Files**: snake_case matching module name (`schema.py`, `rules.py`)

### 6. Type Hints

All functions must have proper type hints:

```python
def analyze_schema(before: List[TableSchema], after: List[TableSchema]) -> RiskAssessment:
    """Analyze schema changes and return risk assessment."""
    pass

def rule_column_added(diff: SchemaDiff) -> List[Finding]:
    """Detect added columns."""
    pass
```

### 7. Testing Patterns

Use pytest with Pydantic model fixtures:

```python
def test_column_diff_detection():
    col = ColumnSchema(
        schema_name="PUBLIC",
        table_name="USERS", 
        column_name="EMAIL",
        data_type="VARCHAR",
        is_nullable=True,
        ordinal_position=1
    )
    table = TableSchema(schema_name="PUBLIC", table_name="USERS", columns=[col])
    # Test logic...
```

Tests should verify:
- Diff detection accuracy
- Rule application correctness  
- Risk scoring determinism
- CLI exit codes

### 8. CLI Design

CLI uses subcommands with Pydantic argument parsing:
- `scia analyze --before before.json --after after.json --format {json|markdown}`
- `scia diff --before before.json --after after.json`

Exit codes: 0 (success), 1 (matches fail-on threshold)

### 9. Output Rendering

JSON output structure:
```python
{
  "risk_score": 80,
  "classification": "HIGH", 
  "findings": [
    {
      "finding_type": "COLUMN_REMOVED",
      "severity": "HIGH",
      "base_risk": 80,
      "evidence": {"schema": "PUBLIC", "table": "USERS", "column": "EMAIL"},
      "description": "Column 'EMAIL' removed from table 'USERS'"
    }
  ]
}
```

### 10. Critical Invariants

**Non-negotiable ground rules:**
- Target warehouse: Snowflake only
- Execution: Local, read-only
- Language: Python 3.9+
- Rules: Hard-coded, deterministic
- Output: JSON first
- Graceful degradation: Missing signals → omitted findings

**Architecture principles:**
- Determinism: Same input → same output, always
- Local execution: No SaaS, no cloud calls (except Snowflake metadata)
- Read-only: Never modify warehouse state
- No ML/guessing: Hard-coded rules only

## Adding New Components

### New Rules
1. Add `FindingType` enum value in `models/finding.py`
2. Implement `def rule_[name](diff: SchemaDiff) -> List[Finding]` in `core/rules.py`
3. Add to `ALL_RULES` list
4. Add corresponding test in `tests/test_rules.py`

### New Output Format
1. Create `render_[format](assessment: RiskAssessment) -> str` in `output/[format].py`
2. Integrate into CLI `--format` choices
3. Add tests in `tests/test_output.py`

### New Warehouse Support
1. Implement adapter in `warehouse/[warehouse].py`
2. Return normalized `List[TableSchema]` objects
3. Handle failures gracefully
4. Add tests in `tests/warehouse/`

## Key Dependencies

- **pydantic>=2.0.0**: Data validation
- **sqlglot>=20.0.0**: SQL parsing (Snowflake dialect)
- **snowflake-connector-python>=3.0.0**: Snowflake metadata
- **pytest>=7.0.0**: Testing framework

## File Structure

```
scia/
├── models/          # Pydantic data models
├── core/            # Diff, rules, risk, analysis logic
├── cli/             # Command-line interface
├── output/          # JSON/Markdown renderers
├── sql/             # SQL parsing and heuristics
├── warehouse/       # Warehouse adapters
├── metadata/        # Metadata fetching
├── input/           # Input resolution
└── config/          # Configuration management
```

## Final Guidelines

> **Correctness, determinism, and trust are more important than completeness.**

If unsure, emit fewer findings rather than false positives. Let users add rules rather than debug incorrect analysis.