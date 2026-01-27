# SCIA AI Coding Agent Instructions

**SCIA (Schema Change Impact Analyzer)** is a deterministic, SQL-first risk assessment tool for schema changes. This guide helps AI agents understand its architecture, patterns, and development model.

⚠️ **DO NOT change scope, order, or architecture.**  
⚠️ **DO NOT introduce new features or abstractions.**  
⚠️ **Follow the deterministic model — correctness over completeness.**

If an instruction conflicts with your intuition, **correctness wins**.

## Architecture Overview

SCIA operates as a **linear, deterministic pipeline**:

```
Input Loader → Schema Diff → Rule Engine → Risk Aggregator → Output Renderer
```

- **Input**: JSON schema files (before/after) with `[TableSchema]` lists
- **Diff Engine** (`core/diff.py`): Detects 4 change types: ADDED, REMOVED, TYPE_CHANGED, NULLABILITY_CHANGED
- **Rule Engine** (`core/rules.py`): Applies deterministic rules to findings (never guesses)
- **Risk Aggregator** (`core/risk.py`): Sums base_risk scores, classifies into LOW (<30), MEDIUM (30-69), HIGH (≥70)
- **Output**: JSON or Markdown with risk_score, classification, findings list

## Core Patterns & Conventions

### 1. Data Models (Pydantic BaseModel)

All data structures use Pydantic BaseModel in `models/`:
- **ColumnSchema**: Represents a column with required fields: `schema_name`, `table_name`, `column_name`, `data_type`, `is_nullable`, `ordinal_position`
- **TableSchema**: List of `ColumnSchema` objects
- **ColumnDiff**: Wraps a single change with `change_type` (ADDED|REMOVED|TYPE_CHANGED|NULLABILITY_CHANGED), `before`, `after`
- **SchemaDiff**: Container for `column_changes: List[ColumnDiff]`
- **Finding**: Risk finding with `finding_type`, `severity`, `base_risk`, `evidence`, `description`

All models are immutable, validated on construction. Never mutate them after creation.

### 2. Rule Application Pattern

Rules follow a strict **function → List[Finding]** pattern in `core/rules.py`:

```python
def rule_column_removed(diff: SchemaDiff) -> List[Finding]:
    """Each rule inspects diff and emits findings."""
    findings = []
    for change in diff.column_changes:
        if change.change_type == 'REMOVED':
            findings.append(Finding(...))
    return findings

ALL_RULES = [rule_column_removed, rule_column_type_changed, ...]
```

**Never**:
- Return early on first match
- Modify diff in-place
- Make assumptions about missing signals
- Score with floating-point (use integer base_risk)

### 3. Graceful Degradation

Missing signals (SQL definitions, query history, Snowflake metadata) should **not emit findings** — they should **omit related findings**:

- No JOIN/GROUP BY analysis without SQL definitions? Skip those finding types.
- No metadata on column usage? Skip usage-based risk signals.
- No query history? Skip adoption-based scoring.

SCIA never guesses. If you can't verify it, don't report it.

### 4. CLI Design (Pydantic Argument Parsing)

`cli/main.py` defines subcommands:

- `scia analyze --before before.json --after after.json --format {json|markdown} --fail-on {HIGH|MEDIUM|LOW}`
- `scia diff --before before.json --after after.json` (returns raw ColumnDiff list)

Exit codes:
- `0`: Success (or below fail-on threshold)
- `1`: Matches fail-on classification

Load schemas as `List[TableSchema]` from JSON files using:
```python
json.load(f)  # File must contain list or single object
[TableSchema(**t) for t in data] if isinstance(data, list) else [TableSchema(**data)]
```

### 5. Output Rendering

**JSON** (`output/json.py`):
```python
{
  "risk_score": 80,
  "classification": "HIGH",
  "findings": [
    {
      "finding_type": "COLUMN_REMOVED",
      "severity": "HIGH",
      "base_risk": 80,
      "evidence": {"table": "orders", "column": "user_id"},
      "description": "..."
    }
  ]
}
```

**Markdown** (`output/markdown.py`): Human-readable summary with findings table.

Both renderers accept `RiskAssessment` object (has `.findings`, `.risk_score`, `.classification`).

## Development Workflow

### Testing Pattern

Use `pytest` with Pydantic model fixtures:
```python
col = ColumnSchema(schema_name="S", table_name="T", column_name="C", 
                   data_type="INT", is_nullable=True, ordinal_position=1)
table = TableSchema(schema_name="S", table_name="T", columns=[col])
```

Tests should verify:
- Diff detection (no-op, additions, removals, type/nullability changes)
- Rule application (each rule emits correct findings)
- Risk scoring (sums correctly, classifies correctly)

### Adding New Rules

1. Define new `FindingType` enum value in `models/finding.py`
2. Implement `def rule_[name](diff: SchemaDiff) -> List[Finding]` in `core/rules.py`
3. Add to `ALL_RULES` list
4. Add corresponding test in `tests/`

Rules are applied in order; aggregate all findings (never short-circuit).

## Critical Design Invariants (v0.1)

**Non-Negotiable Ground Rules:**

1. Target warehouse: **Snowflake only**
2. Execution: **local, read-only**
3. Language: **Python**
4. Packaging: **pip-installable**
5. Rules: **hard-coded, deterministic**
6. Output: **JSON first**
7. Authoritative Documentation (Read-Only)

These documents lock v0.1 scope and must NOT be modified without major version bump:
- `design.md` — Locked architecture decisions
- `REQUIREMENTS.md` — Functional specification (v0.2 extended)
- Add BI integrations
- Add ML/AI logic
- Add dbt dependency
- Add network calls beyond Snowflake

**Architecture Invariants:**
- **Determinism**: Same input → same output, always
- **Local execution**: No SaaS, no cloud calls (except Snowflake metadata read)
- **Read-only**: Never modify warehouse state
- **SQL-first, dbt-optional**: Works with raw SQL, dbt enriches but not required
- **No ML/guessing**: Hard-coded rules only
- **Fail CI on HIGH**: Non-zero exit code by default
- **Graceful degradation**: Missing signals → omitted findings, not errors

## Files Not to Modify

- `coding_agent_instructions.md` — Authoritative scope definition
- `design.md` — Locked architecture decisions
- `REQUIREMENTS.md` — Functional specification

## Key Dependencies

- **Pydantic ≥2.0.0**: Data validation
- **sqlglot ≥20.0.0**: Best-effort SQL parsing (Snowflake dialect)
- **snowflake-connector-python ≥3.0.0**: Metadata reads (future use)
- **pytest ≥7.0.0**: Testing

## Import Structure

```
from scia.models.schema import ColumnSchema, TableSchema
from scia.models.finding import Finding, FindingType, Severity
from scia.core.diff import diff_schemas, SchemaDiff
from scia.core.rules import apply_rules
from scia.core.risk import RiskAssessment
from scia.output.json import render_json
from scia.output.markdown import render_markdown
```

Never import internal functions or create circular dependencies.

## Implementation Checklist for v0.1

Before declaring any feature complete, verify:

- [ ] Schema diff works without SQL
- [ ] SQL parsing failures do not crash (graceful degradation)
- [ ] Rules emit findings **only with evidence** (never guess)
- [ ] Risk scoring is deterministic (integer base_risk, additive)
- [ ] CLI exits non-zero on HIGH risk
- [ ] JSON output schema is stable
- [ ] No SaaS assumptions anywhere
- [ ] No dbt dependency anywhere

## Component-Specific Patterns

### Adding New Rules

**Location**: `scia/core/rules.py`

1. Define new `FindingType` enum value in `models/finding.py`
2. Implement rule as pure function:
   ```python
   def rule_[name](diff: SchemaDiff) -> List[Finding]:
       findings = []
       for change in diff.column_changes:
           if change.change_type == 'SOME_TYPE':
               findings.append(Finding(...))
       return findings
   ```
3. Add to `ALL_RULES` list (order matters for determinism)
4. Add test in `tests/test_rules.py` (or equivalent)

**Rules MUST NOT:**
- Return early on first match (aggregate all findings)
- Modify diff in-place
- Guess when evidence is missing
- Depend on execution order (pure functions only)

### Adding New Output Format

**Location**: `scia/output/[format].py`

1. Create `render_[format](assessment: RiskAssessment) -> str` function
2. Accept `RiskAssessment` object (has `.findings`, `.risk_score`, `.classification`)
3. Return formatted string
4. Integrate into CLI `--format` choices

### Adding Metadata Source

**Location**: `scia/metadata/[warehouse].py`

1. Implement adapter to fetch schema metadata
2. Return normalized `List[TableSchema]` objects
3. Handle failures gracefully (warn, not crash)
4. Respect read-only semantics (no modifications)

### Debugging Pipeline

**Flow**: Input → Diff → SQL Signals → Rules → Risk → Output

Always start by understanding the diff:
```python
from scia.core.diff import diff_schemas
diff = diff_schemas(before_schemas, after_schemas)
print(diff.column_changes)
```

Then trace which rules match:
```python
from scia.core.rules import apply_rules
findings = apply_rules(diff)
for f in findings:
    print(f"Rule: {f.finding_type}, Evidence: {f.evidence}")
```

## Final Instruction

> **Correctness, determinism, and trust are more important than completeness.**

If unsure, **emit fewer findings**, not more. Let users add rules rather than debug false positives.
