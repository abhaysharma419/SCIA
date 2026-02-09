# Schema Change Impact Analyzer (SCIA)

**Predict schema change risks before they break production.**

SCIA analyzes SQL schema changes and tells you:
- ✅ What will break
- ✅ How risky it is (LOW/MEDIUM/HIGH)
- ✅ Why it matters

Works with JSON exports, SQL migration files, or live warehouse connections.

---

## 🚀 Quick Start

### 1. Install

```bash
pip install scia-core
```

### 2. Prepare Schema Files

Create two JSON files representing your schema before and after the change:

**`before_schema.json`** — Original schema
```json
[
  {
    "schema_name": "analytics",
    "table_name": "customers",
    "columns": [
      {
        "column_name": "customer_id",
        "data_type": "INT",
        "is_nullable": false,
        "ordinal_position": 1
      },
      {
        "column_name": "email",
        "data_type": "VARCHAR",
        "is_nullable": true,
        "ordinal_position": 2
      }
    ]
  }
]
```

**`after_schema.json`** — Modified schema (e.g., removed `email` column)
```json
[
  {
    "schema_name": "analytics",
    "table_name": "customers",
    "columns": [
      {
        "column_name": "customer_id",
        "data_type": "INT",
        "is_nullable": false,
        "ordinal_position": 1
      }
    ]
  }
]
```

### 3. Run Analysis

**JSON Mode (Offline):**
```bash
scia analyze --before before_schema.json --after after_schema.json --format markdown
```

**SQL Mode (Migration Analysis):**
Analyze risk of applying a SQL migration to an existing schema (JSON or DB).
```bash
# Apply migration.sql to schema in base_schema.json
scia analyze --before base_schema.json --after migration.sql --format markdown

# Specify dialect for SQL parsing (currently only snowflake fully supported)
scia analyze --before base_schema.json --after migration.sql --dialect snowflake --format markdown
```
*Supported ALTER operations:* `ADD COLUMN`, `DROP COLUMN`, `RENAME COLUMN`, `ALTER COLUMN (TYPE/NULLABILITY)`.

**Database Mode (Live):**
```bash
scia analyze --before PROD.ANALYTICS --after DEV.ANALYTICS --warehouse snowflake --format markdown
```

### 4. Get Risk Assessment

Output (Markdown):
```
RISK: HIGH
Classification: HIGH
Risk Score: 80

Findings:
1. COLUMN_REMOVED (Severity: HIGH)
   - Column 'email' removed from table 'customers'
   - Evidence: table=customers, column=email
```

> [!NOTE]
> **New to v0.2?** Check out the [Advanced Usage Guide](docs/USAGE_V02.md) for SQL migration analysis, live database connections, and dependency analysis features.

---

## 📋 Common Use Cases

### Use Case 1: Column Removal

**Scenario:** Remove a column you think is unused

```bash
scia analyze \
  --before before_schema.json \
  --after after_schema.json \
  --format markdown
```

**Output:** 
- ✅ Detects if downstream views depend on this column
- ✅ Warns about join key changes
- ✅ Scores risk (HIGH if widely used)

### Use Case 2: Type Change

**Scenario:** Change INT column to STRING

```bash
# before_schema.json: "data_type": "INT"
# after_schema.json: "data_type": "VARCHAR"

scia analyze \
  --before before_schema.json \
  --after after_schema.json \
  --format json
```

**Output:** 
- ✅ Identifies type incompatibility
- ✅ Warns about casting issues
- ✅ Risk: MEDIUM (may break queries)

### Use Case 3: Nullability Change

**Scenario:** Make nullable column NOT NULL

```bash
# before_schema.json: "is_nullable": true
# after_schema.json: "is_nullable": false

scia analyze \
  --before before_schema.json \
  --after after_schema.json \
  --format json
```

**Output:**
- ✅ Detects NOT NULL constraint
- ✅ Warns about NULL values in production
- ✅ Risk: MEDIUM (data quality issue)

---

## 📊 Output Formats

### Markdown (Human-Readable)

```bash
scia analyze --before before_schema.json --after after_schema.json --format markdown
```

**Output:**
```
# Risk Assessment: HIGH

## Findings (3)

| Finding Type | Severity | Risk | Evidence |
|---|---|---|---|
| COLUMN_REMOVED | HIGH | 80 | {table: users, column: user_id} |
| COLUMN_TYPE_CHANGED | MEDIUM | 40 | {...} |
| ...| | | |
```

### JSON (Machine-Readable)

```bash
scia analyze --before before_schema.json --after after_schema.json --format json
```

**Output:**
```json
{
  "risk_score": 120,
  "classification": "HIGH",
  "findings": [
    {
      "finding_type": "COLUMN_REMOVED",
      "severity": "HIGH",
      "base_risk": 80,
      "evidence": {"table": "users", "column": "user_id"},
      "description": "Column 'user_id' removed from table 'users'."
    }
  ]
}
```

---

## 🔧 CLI Reference

### Basic Command

```bash
scia analyze --before <before.json> --after <after.json> [options]
```

### Options

| Option | Required | Example | Description |
|--------|----------|---------|-------------|
| `--before` | ✅ | `before.json` | Original schema (JSON, SQL, or SCHEMA.TABLE) |
| `--after` | ✅ | `after.json` | Modified schema (JSON, SQL, or SCHEMA.TABLE) |
| `--warehouse` | ❌ | `snowflake` | Warehouse type (required for DB mode) |
| `--conn-file` | ❌ | `config.yaml` | Connection config file |
| `--dependency-depth`| ❌ | `3` | Max depth for dependency analysis (1-10) |
| `--dialect` | ❌ | `snowflake` | SQL dialect for parsing (snowflake, postgres, mysql, bigquery, databricks, redshift). Default: snowflake. **Note: Only snowflake dialect is fully supported currently.** |
| `--format` | ❌ | `json` or `markdown` | Output format (default: json) |
| `--fail-on` | ❌ | `HIGH` | Exit code 1 if risk meets threshold |

### Exit Codes

- `0` — Success (risk below threshold or below `--fail-on`)
- `1` — Risk matches `--fail-on` threshold

### Example: Use in CI/CD

```bash
# Fail CI if HIGH risk detected
scia analyze --before before.json --after after.json --fail-on HIGH
```

---

## 💡 Examples

### Example 1: Safe Column Addition

**before.json:**
```json
[{"schema_name": "db", "table_name": "orders", "columns": [...]}]
```

**after.json:**
```json
[{"schema_name": "db", "table_name": "orders", "columns": [..., {"column_name": "order_notes", "data_type": "VARCHAR", "is_nullable": true, "ordinal_position": 5}]}]
```

**Command:**
```bash
scia analyze --before before.json --after after.json --format markdown
```

**Result:** ✅ `RISK: LOW` — New nullable column is safe

---

### Example 2: Risky Column Removal

**before.json:**
```json
[{"schema_name": "db", "table_name": "users", "columns": [{"column_name": "user_id", ...}, ...]}]
```

**after.json:**
```json
[{"schema_name": "db", "table_name": "users", "columns": [...]}]  # user_id removed
```

**Command:**
```bash
scia analyze --before before.json --after after.json --format markdown
```

**Result:** ⚠️ `RISK: HIGH` — Primary key removed, will break joins

---

## 📂 Project Structure

```
SCIA/
├── .github/copilot-instructions.md    (AI agent guidance)
├── AI_QUICK_REFERENCE.md              (Quick reference)
├── README.md                          (This file)
│
├── docs/                              (Documentation)
│   ├── design.md                      (Architecture)
│   ├── REQUIREMENTS.md                (Functional spec)
│   └── FOLDER_STRUCTURE.md            (Project organization)
│
├── scia/                              (Source code)
│   ├── cli/main.py                    (Command-line interface)
│   ├── core/                          (Analysis engine)
│   │   ├── diff.py                    (Schema comparison)
│   │   ├── rules.py                   (Risk rules)
│   │   └── risk.py                    (Risk scoring)
│   ├── models/                        (Data models)
│   ├── output/                        (Renderers)
│   └── sql/                           (SQL parsing)
│
├── tests/                             (Tests)
│   ├── test_diff.py
│   ├── test_rules.py
│   └── fixtures/                      (Test data)
│       ├── before.json
│       ├── after.json
│       └── after_medium.json
│
└── pyproject.toml                     (Package config)
```

---

## 🏗️ What SCIA Does (v0.2)

**Detects:**
- Column removal, type changes, nullability changes
- **JOIN key breakage** (High Risk)
- **GROUP BY grain changes** (Medium Risk)
- **Downstream view breakage** (Transitive impact)

**Scores risk as:**
- **LOW** (<30) — Safe to deploy
- **MEDIUM** (30-69) — Review recommended
- **HIGH** (≥70) — Likely to break systems

**Outputs:**
- JSON with `impact_detail`
- Markdown with "Downstream Impact" tables

---

## 🚫 What SCIA Does NOT Do

- ❌ Modify your schema
- ❌ Connect to your warehouse (uses JSON exports)
- ❌ Require a metadata catalog
- ❌ Lock you into a vendor
- ❌ Support dbt as a requirement (only optional enrichment)

---

## 🛠️ For Developers

### Run Tests

```bash
pytest tests/
```

### Run a Specific Test

```bash
pytest tests/test_diff.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=scia
```

### Develop & Install in Editable Mode

```bash
pip install -e .
```

---

## 📚 Documentation

- **[docs/design.md](docs/design.md)** — Architecture & design decisions
- **[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)** — Functional specification
- **[docs/FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md)** — Project organization
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** — AI agent guidance (for developers extending SCIA)

---

## 🎯 Risk Scoring

## 🎯 Risk Scoring

Each change type gets a base risk score:

| Change Type | Base Risk | Why |
|-------------|-----------|-----|
| Column removed | 80 | Breaks joins, aggregations |
| Type changed | 40 | May cause casting errors |
| Nullability changed | 50 | Data quality issues |
| Column added (nullable) | 0 | Safe — won't break anything |

**Total risk = Sum of all findings**

- **LOW** (<30): Safe to deploy
- **MEDIUM** (30-69): Review before deploying
- **HIGH** (≥70): Likely to break downstream systems

---

## 💡 Tips

### Tip 1: Export Snowflake Schema

To get schema JSON from Snowflake:

```sql
SELECT 
  table_schema as schema_name,
  table_name,
  column_name,
  data_type,
  is_nullable,
  ordinal_position
FROM information_schema.columns
WHERE table_schema = 'ANALYTICS'
ORDER BY table_name, ordinal_position;
```

Export as JSON and use with SCIA.

### Tip 2: Use in CI/CD

Add to your deployment pipeline:

```yaml
# GitHub Actions example
- name: Check schema changes
  run: |
    scia analyze --before before.json --after after.json --fail-on HIGH
    # Job fails if HIGH risk detected
```

### Tip 3: Compare Multiple Scenarios

```bash
# Scenario 1: Remove column
scia analyze --before base.json --after scenario1.json

# Scenario 2: Change type
scia analyze --before base.json --after scenario2.json

# Pick the safer approach
```

---

## 🔧 Troubleshooting

### Connection Issues

**Problem**: `Error: Connection failed to snowflake`

**Solutions**:
1. Verify config file exists: `ls ~/.scia/snowflake.yaml`
2. Check credentials in config file
3. Ensure account identifier is correct (format: `account.region.snowflakecomputing.com`)
4. Use `--conn-file` to specify custom config location

**Example**:
```bash
# Use custom config file
scia analyze --before PROD.ANALYTICS --after DEV.ANALYTICS \
  --warehouse snowflake --conn-file ~/my-config.yaml
```

---

### SQL Parsing Errors

**Problem**: `Warning: Failed to parse SQL in migration.sql`

**Explanation**: SCIA supports CREATE TABLE, ALTER ADD/DROP/MODIFY/RENAME COLUMN. Other DDL is ignored.

**What Happens**: Analysis continues with schema-based rules only (no SQL-specific rules).

**Supported Operations**:
- ✅ `CREATE TABLE`
- ✅ `ALTER TABLE ADD COLUMN`
- ✅ `ALTER TABLE DROP COLUMN`
- ✅ `ALTER TABLE RENAME COLUMN`
- ✅ `ALTER TABLE ALTER COLUMN` (type/nullability changes)
- ❌ Stored procedures, triggers, constraints (ignored)

---

### Dependency Analysis Errors

**Problem**: `Error: max_depth must be 1-10, got 15`

**Solution**: Use `--dependency-depth` with value between 1 and 10:
```bash
scia analyze --before a.json --after b.json --dependency-depth 5
```

---

**Problem**: `Error: DB mode requires --warehouse flag`

**Solution**: Add `--warehouse` when comparing database identifiers:
```bash
scia analyze --before PROD.ANALYTICS --after DEV.ANALYTICS --warehouse snowflake
```

---

### Unsupported Warehouse

**Problem**: `Error: Databricks adapter not yet implemented`

**Current Support**:
- ✅ Snowflake (fully working)
- 🏗️ Databricks (planned for v0.3)
- 🏗️ PostgreSQL (planned for v0.3)
- 🏗️ Redshift (planned for v0.3)

**Workaround**: Export your schema to JSON and use JSON mode:
```bash
scia analyze --before schema.json --after modified.json
```

---

## ❓ FAQ

**Q: Can SCIA connect to my warehouse directly?**  
A: Yes! v0.2 supports live connections to Snowflake. Use `--warehouse snowflake` and configure `~/.scia/snowflake.yaml`. See the [Advanced Usage Guide](docs/USAGE_V02.md) for details.

**Q: Do I need dbt?**  
A: No. SCIA works with plain SQL, JSON exports, and warehouse metadata.

**Q: What warehouses are supported?**  
A: v0.2 fully supports Snowflake. Databricks, PostgreSQL, and Redshift are planned for v0.3.

**Q: What if my schema has thousands of columns?**  
A: SCIA analyzes the diff, not absolute size. Performance should be acceptable. Use `--dependency-depth 1` for faster analysis.

**Q: Can I use this in production?**  
A: Yes! v0.2 is production-ready. Start with JSON mode for testing, then enable live warehouse connections. See [docs/USAGE_V02.md](docs/USAGE_V02.md) for best practices.

---

## 🤝 Contributing

We welcome contributions! See [.github/copilot-instructions.md](.github/copilot-instructions.md) for development guide.

Areas for contribution:
- Warehouse adapters (BigQuery, Databricks, PostgreSQL)
- SQL heuristics improvements
- Real-world incident patterns
- Testing edge cases

---

## 📄 License

Apache 2.0 — See LICENSE file

---

## 🚀 What's Next?

- **v0.1** ✅: Core schema diff, risk scoring, JSON-based analysis
- **v0.2** ✅: SQL migration parsing, live warehouse connectivity (Snowflake), downstream impact analysis
- **v0.3** 🏗️: Multi-warehouse support (Databricks, PostgreSQL, Redshift), advanced risk policies, incident pattern matching

---

## 💬 Questions?

- Check [docs/USAGE_V02.md](docs/USAGE_V02.md) for advanced v0.2 features
- See [DOCS_INDEX.md](DOCS_INDEX.md) for all documentation
- Read [docs/FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md) for project layout
- Check [.github/copilot-instructions.md](.github/copilot-instructions.md) for architecture



