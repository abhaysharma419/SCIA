# SCIA v0.1 — Coding Agent Instructions (Authoritative)

This document provides **strict, step‑by‑step instructions** for implementing SCIA v0.1.

⚠️ **DO NOT change scope, order, or architecture.**  
⚠️ **DO NOT introduce new features or abstractions.**  
⚠️ **Follow steps sequentially.**

If an instruction conflicts with your intuition, **the instruction wins**.

---

## 0. Ground Rules (Non‑Negotiable)

1. Target warehouse: **Snowflake only**
2. Execution: **local, read‑only**
3. Language: **Python**
4. Packaging: **pip‑installable**
5. Rules: **hard‑coded, deterministic**
6. Output: **JSON first**
7. CI behavior: **exit non‑zero on HIGH risk**
8. Graceful degradation on missing metadata

Do NOT:
- Add SaaS components
- Add BI integrations
- Add ML/AI logic
- Add dbt dependency
- Add network calls beyond Snowflake

---

## 1. Repository Bootstrap

### 1.1 Create base structure

Create the following directories exactly:

```
scia/
├── docs/
├── scia/
│ ├── cli/
│ ├── core/
│ ├── metadata/
│ ├── sql/
│ ├── models/
│ └── output/
├── tests/
├── pyproject.toml
└── README.md
```

Do NOT add additional top‑level folders.

---

## 2. Define Core Data Models (FIRST)

### 2.1 Implement schema models

Location: `scia/models/schema.py`

Must define:
- `TableSchema`
- `ColumnSchema`

Required fields (minimum):
- table_name
- schema_name
- column_name
- data_type
- is_nullable
- ordinal_position

No warehouse logic allowed here.

---

### 2.2 Implement finding models

Location: `scia/models/finding.py`

Must define:
- `FindingType` (Enum)
- `Severity` (Enum)
- `Finding` (Pydantic or dataclass)

`Finding` MUST include:
- finding_type
- severity
- base_risk
- evidence (dict)
- confidence (optional)

Do NOT add dynamic fields.

---

## 3. Metadata Inspector (Snowflake Only)

### 3.1 Implement Snowflake adapter

Location: `scia/metadata/snowflake.py`

Responsibilities:
- Connect to Snowflake (read‑only)
- Fetch:
  - `information_schema.columns`
  - `information_schema.views`
  - view definitions

Return normalized `TableSchema` / `ColumnSchema` objects.

Do NOT:
- Modify data
- Cache externally
- Assume privileges beyond information_schema

---

### 3.2 Acceptance Criteria

- Inspector works with read‑only role
- Inspector failures do NOT crash entire run
- Errors are surfaced as warnings

---

## 4. Schema Diff Engine (NO SQL YET)

### 4.1 Implement diff logic

Location: `scia/core/diff.py`

Responsibilities:
- Compare before vs after schemas
- Emit structural changes only

Must detect:
- Column added
- Column removed
- Data type changed
- Nullability changed

Output should be **raw diffs**, not findings.

---

### 4.2 Tests (MANDATORY)

Location: `tests/test_diff.py`

Include tests for:
- Column removal
- Type change
- Nullability change
- No‑op diff

DO NOT proceed without passing tests.

---

## 5. Deterministic Rule Engine

### 5.1 Implement rules

Location: `scia/core/rules.py`

Each rule:
- Is a pure function
- Consumes diffs + optional SQL signals
- Emits **zero or more Findings**
- Requires explicit evidence

Rules MUST NOT:
- Suppress other rules
- Guess when evidence is missing
- Depend on execution order

Use the predefined rule → finding mapping from DESIGN.md.

---

### 5.2 Risk Aggregation

Location: `scia/core/risk.py`

Responsibilities:
- Sum base_risk from all findings
- Classify overall risk:
  - LOW < 30
  - MEDIUM 30–69
  - HIGH ≥ 70

No weighting. No heuristics.

---

## 6. SQL Parsing & Heuristics (AFTER RULES)

### 6.1 Implement SQL parser

Location: `scia/sql/parser.py`

Scope:
- SELECT
- JOIN
- GROUP BY
- WHERE

Policy:
- Best‑effort parsing
- If parsing fails → return empty result
- NEVER raise fatal exception

---

### 6.2 Implement heuristics

Location: `scia/sql/heuristics.py`

Extract:
- Join keys
- Group by columns
- Predicate usage

These signals are **optional inputs** to rules.

---

## 7. Orchestration Layer

### 7.1 Implement analyzer

Location: `scia/core/analyze.py`

Responsibilities:
1. Load inputs
2. Fetch metadata (if live)
3. Diff schemas
4. Parse SQL (if available)
5. Apply rules
6. Aggregate risk
7. Produce result object

No CLI logic here.

---

## 8. Output Rendering

### 8.1 JSON output (PRIMARY)

Location: `scia/output/json.py`

Must output:
- risk_score
- classification
- findings (list)

Ensure stable schema.

---

### 8.2 Markdown output (OPTIONAL)

Location: `scia/output/markdown.py`

Human‑readable summary only.

---

## 9. CLI Interface (LAST)

### 9.1 Implement CLI

Location: `scia/cli/main.py`

Commands:
- `scia analyze`
- `scia diff`

Flags:
- --warehouse
- --conn
- --before / --after
- --sql-dir
- --fail-on

---

### 9.2 Exit Code Rules

- HIGH risk → exit code `1`
- Otherwise → exit code `0`

This behavior is **default**.

---

## 10. Packaging

### 10.1 pyproject.toml

Ensure:
- Proper entrypoint for CLI
- Minimal dependencies
- Python ≥ 3.9

---

## 11. Final Validation Checklist (MUST PASS)

Before declaring completion:

- [ ] Schema diff works without SQL
- [ ] SQL parsing failures do not crash
- [ ] Rules emit findings only with evidence
- [ ] Risk scoring is deterministic
- [ ] CLI exits non‑zero on HIGH
- [ ] JSON output is stable
- [ ] No SaaS assumptions
- [ ] No dbt dependency

---

## 12. Stop Condition

Once all steps pass:
- STOP
- Do NOT refactor
- Do NOT optimize
- Do NOT add features

SCIA v0.1 is **complete at this point**.

---

## Final Instruction

> Correctness, determinism, and trust are more important than completeness.

If unsure, **emit fewer findings**, not more.