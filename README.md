# Schema Change Impact Agent (SCIA)

Predict downstream impact of SQL schema changes before they break production.

**SCIA** is a SQL-first, open-source agent that analyzes schema changes before deployment and tells you what will break, how risky it is, and why — using only existing warehouse metadata and SQL definitions.

- ✅ No catalog required
- ✅ No vendor lock-in
- ✅ No mandatory frameworks

---

## Why SCIA Exists

Every data platform already has:

- SQL tables, views, and procedures
- Warehouse metadata (`information_schema`)
- Query history

Yet schema changes still:

- Break downstream views
- Corrupt metrics silently
- Cause late-night rollbacks

**The problem is not missing metadata. The problem is no automated reasoning over SQL and dependencies.**

SCIA fills that gap.

---

## What SCIA Does

Given a proposed SQL schema change, SCIA:

- ✅ Detects breaking changes
- ✅ Resolves downstream dependencies
- ✅ Identifies grain and join risk
- ✅ Scores deployment risk
- ✅ Explains the impact in plain English

All before the change reaches production.

---

## What SCIA Does Not Do

- ❌ No metadata catalog
- ❌ No data ingestion
- ❌ No enforcement (yet)
- ❌ No dashboards
- ❌ No vendor-specific lock-in

SCIA is intentionally small, composable, and read-only.

---

## SQL-First by Design

SCIA is built around universal primitives:

| Input | Status |
|-------|--------|
| SQL DDL / model changes | ✅ Required |
| Warehouse metadata (`information_schema`) | ✅ Required |
| View / table definitions | ✅ Required |
| Query history | ⭕ Optional |

**DBT is optional, not required.**

If DBT artifacts are present, SCIA uses them to enrich lineage and semantics. If not, SCIA works entirely from SQL and warehouse metadata.

---

## How It Works

SCIA follows a straightforward process:

1. Reads proposed SQL/schema changes
2. Extracts warehouse metadata (read-only)
3. Resolves downstream dependencies
4. Analyzes structural and semantic risk
5. Generates a human-readable impact report

---

## Supported Warehouses

- ✅ **Snowflake** (v0.1)
- 📋 **BigQuery** (planned)
- 📋 **Databricks** (planned)

---

## Installation

```bash
pip install scia
```

---

## Usage

### CLI (SQL-only)

```bash
scia analyze \
  --warehouse snowflake \
  --database analytics \
  --schema mart \
  --changed-object orders
```

### SQL Diff / File-based Analysis

```bash
scia analyze \
  --warehouse snowflake \
  --sql-diff schema_changes.sql
```

### Optional: DBT Enrichment

If DBT artifacts are available, provide them optionally:

```bash
scia analyze \
  --warehouse snowflake \
  --sql-diff schema_changes.sql \
  --dbt-manifest manifest.json \
  --dbt-catalog catalog.json
```

> **Note:** DBT improves confidence — it is never required.

---

## Example Output

```
RISK: HIGH

• Column `customer_id` removed
• 3 downstream views depend on this column
• Revenue aggregation grain may change
• Historical queries rely on this field

Recommendation:
Update dependent views before deployment.
```

Outputs are available as:

- **Markdown** (humans)
- **JSON** (machines)

---

## What Counts as a Schema Change

SCIA currently analyzes:

- Column removal
- Column rename (heuristic)
- Data type change
- Nullability change
- Join key change
- Grain change (heuristic)

These represent the majority of real-world data incidents.

---

## Risk Scoring Model

Each change is scored as:

- **LOW** – Safe change
- **MEDIUM** – Review recommended
- **HIGH** – Likely to break downstream systems

Scores are based on:

- Change type
- Dependency depth
- Query usage patterns
- Semantic indicators (if available)

---

## Design Principles

- 🔧 SQL-first
- 🏭 Warehouse-native
- 🔒 Read-only
- 🎯 Deterministic logic first
- 🤖 LLMs explain, not decide
- ⚙️ CLI & CI over UI
- 🧩 Composable agents, not platforms

---

## Roadmap

### v0.1 (Current)

- SQL-first analysis
- Snowflake metadata
- CLI interface
- Markdown & JSON reports

### v0.2

- Query history-aware impact
- Improved rename detection
- CI / PR comments

### v0.3

- Risk thresholds & policies
- Slack notifications
- Historical incident learning

---

## Who This Is For

- Data Engineers
- Platform Teams
- Warehouse-centric organizations
- SQL-heavy environments
- Teams without DBT (and with DBT)

---

## Why Open Source

SCIA is open source because:

- Schema reasoning should be transparent
- Metadata should not be locked in
- Governance should integrate with SQL workflows

Future paid extensions (optional) may include:

- Audit trails
- Compliance reporting
- Enterprise integrations

**The core agent will remain open.**

---

## Contributing

Contributions welcome:

- Warehouse adapters
- SQL heuristics
- Real-world incident patterns

Open an issue or submit a PR.

---

## License

Apache 2.0

