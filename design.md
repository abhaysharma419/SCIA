# SCIA — Design & Architecture (v0.1)

**SCIA (SQL Change Impact Analyzer)** is a local, deterministic, SQL‑first tool that evaluates the **risk of schema and SQL changes before deployment**.

SCIA is designed to run with **read‑only access**, work with **partial metadata**, and produce **machine‑readable findings** suitable for CI/CD pipelines.

---

## 1. Problem Statement

Modern data teams routinely modify schemas, views, and SQL logic without a deterministic way to understand downstream impact **before changes reach production**.

Common failure modes:
- Silent metric corruption due to JOIN or GROUP BY changes
- Broken views caused by column removals or type changes
- High‑usage columns modified without visibility
- Over‑reliance on tribal knowledge or manual reviews

Existing solutions are often:
- SaaS‑heavy and vendor‑locking
- dbt‑only and ecosystem‑limited
- Lineage‑first but hard to trust
- AI‑driven without deterministic guarantees

**SCIA’s goal** is to provide a **trustworthy, deterministic impact analysis engine** that answers:

> “If this change is applied, what can break — and how risky is it?”

---

## 2. Non‑Goals (Explicit)

SCIA v0.1 explicitly does **NOT** aim to:

- Build full end‑to‑end lineage graphs
- Parse every SQL dialect perfectly
- Integrate deeply with BI tools
- Require dbt, Airflow, or SaaS agents
- Infer business semantics or intent
- Perform automated fixes

SCIA is an **engineering safety tool**, not a governance platform.

---

## 3. Core Design Principles (Invariants)

The following principles must **never** be violated:

1. **SQL‑first, dbt‑optional**
2. **Deterministic rules only**
3. **Evidence‑backed findings**
4. **Graceful degradation with partial metadata**
5. **Local execution, read‑only access**
6. **Machine‑readable output first**
7. **Fail CI on HIGH risk by default**

Any feature violating these principles does not belong in v0.1.

---

## 4. Locked Decisions (v0.1)

These decisions are final for v0.1:

| Area | Decision |
|----|----|
| Initial warehouse | Snowflake |
| Distribution | pip‑installable Python package |
| Execution | Local, read‑only |
| Inputs | Live Snowflake connection **and/or** JSON schema files |
| Rules | Hard‑coded deterministic Python rules |
| SQL philosophy | SQL‑first, dbt‑optional |
| CI behavior | Fail on HIGH risk (non‑zero exit code) |
| Output | JSON primary, Markdown optional |

---

## 5. High‑Level Architecture

### 5.1 System Flow

User / CI
│
▼
Input Loader
(schema, SQL, metadata)
│
▼
Schema Diff Engine
(structural changes only)
│
▼
SQL Parsing & Heuristics
(best‑effort, safe failure)
│
▼
Deterministic Rule Engine
(rule → finding mapping)
│
▼
Risk Aggregator
(additive scoring)
│
▼
Output Renderer
(JSON + exit code)


---

## 6. Input Model

SCIA operates on **layered metadata**. Each layer is optional except the minimum required input.

### 6.1 Required Input (Minimum Viable)

At least **one** of the following must be provided:

- Live Snowflake connection  
- `before_schema.json` and `after_schema.json`

This guarantees SCIA can always run.

---

### 6.2 Optional Inputs (Graceful Degradation)

| Input | Used for |
|----|----|
| View definitions | JOIN / GROUP BY / WHERE detection |
| Stored procedures | ETL SQL impact |
| SQL files | Repo‑based SQL analysis |
| Query history | Usage‑based risk |

If an input is unavailable, related findings are **not emitted**.  
SCIA never guesses.

---

## 7. Internal Components

### 7.1 Metadata Inspector (Snowflake)

**Responsibilities**
- Read `information_schema.columns`
- Read `information_schema.views`
- Normalize schema metadata

**Guarantees**
- Read‑only access
- No mutations
- Minimal permissions

---

### 7.2 Schema Diff Engine

**Responsibilities**
- Compare before vs after schema
- Emit raw structural deltas

**Outputs**
- Column added
- Column removed
- Data type changed
- Nullability changed

No risk logic exists in this layer.

---

### 7.3 SQL Parsing & Heuristics

**Responsibilities**
- Parse SQL into AST (best‑effort)
- Extract:
  - JOIN keys
  - GROUP BY columns
  - WHERE predicates
  - Selected columns

**Failure policy**
- If SQL cannot be parsed → skip SQL‑based rules
- Never fail the run due to SQL complexity

---

### 7.4 Rule Engine (Core Logic)

**Responsibilities**
- Apply deterministic rule → finding mappings
- Emit findings **only when evidence exists**

Rules are:
- Stateless
- Order‑independent
- Pure functions
- Hard‑coded in Python

No learning, no probabilities (except explicit confidence flags).

---

### 7.5 Risk Aggregator

**Responsibilities**
- Aggregate base risk scores
- Classify overall risk

**Thresholds**
- LOW: < 30
- MEDIUM: 30–69
- HIGH: ≥ 70

Risk is additive. No hidden weighting.

---

### 7.6 Output & Exit Codes

**Primary Output (JSON)**

```json
{
  "risk_score": 85,
  "classification": "HIGH",
  "findings": [...]
}
```

**Exit Behavior**

- HIGH risk → exit code 1
- Otherwise → exit code 0

Configurable via:

```bash
--fail-on HIGH
```

(Default: enabled)

### 8.1 CLI (Primary Interface)

```bash
scia analyze \
  --warehouse snowflake \
  --conn snowflake://... \
  --sql-dir ./sql \
  --fail-on HIGH
scia diff \
  --before before.json \
  --after after.json
```

### 8.2 Python API

```python
from scia import analyze

result = analyze(
    warehouse="snowflake",
    connection=conn,
    before_schema=before,
    after_schema=after,
    sql_sources=sql_files,
    fail_on="HIGH"
)
```
## 9. Repository Structure

```
scia/
├── docs/
│   ├── DESIGN.md
│   ├── RULES.md
│   └── LIMITATIONS.md
├── scia/
│   ├── cli/
│   ├── core/
│   │   ├── diff.py
│   │   ├── rules.py
│   │   └── risk.py
│   ├── metadata/
│   │   └── snowflake.py
│   ├── sql/
│   │   ├── parser.py
│   │   └── heuristics.py
│   ├── models/
│   └── output/
├── tests/
├── pyproject.toml
└── README.md
```
## 10. Execution Roadmap

### Phase 0 — Design Lock (Completed)
- Architecture frozen
- Rules defined
- Scope fixed

### Phase 1 — Schema Diff MVP
- Schema models
- Snowflake metadata reader
- Diff engine
- JSON output
- Tests

### Phase 2 — SQL Parsing
- SELECT / JOIN / GROUP BY support
- Safe failure modes
- SQL parsing tests

### Phase 3 — Rule Engine
- Implement all deterministic rules
- Evidence enforcement
- Risk aggregation

### Phase 4 — CLI & Packaging
- CLI commands
- CI‑friendly exit codes
- pip packaging
- README examples

11. Coding Agent Instructions (Critical)
The coding agent must follow this order:

Implement schema models

Implement Snowflake metadata inspector

Implement schema diff engine

Write diff tests

Implement rule engine

Only then add SQL parsing

Any deviation risks architectural breakage.

12. Final Design Statement
SCIA prioritizes correctness, determinism, and trust over completeness.

It emits only what it can prove with evidence, degrades safely with missing metadata, and integrates cleanly into modern CI/CD workflows.

This document is the authoritative reference for SCIA v0.1.