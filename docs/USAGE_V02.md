# SCIA v0.2 Advanced Usage Guide

This guide covers advanced features introduced in SCIA v0.2, including SQL migration analysis, live database connections, and dependency impact analysis.

---

## Table of Contents

1. [SQL Migration Analysis](#sql-migration-analysis)
2. [Live Database Comparison](#live-database-comparison)
3. [Dependency Analysis Configuration](#dependency-analysis-configuration)
4. [Upstream & Downstream Analysis](#upstream--downstream-analysis)
5. [Connection Configuration](#connection-configuration)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## SQL Migration Analysis

Analyze the risk of applying SQL migration files to your existing schema.

### Supported DDL Operations

SCIA v0.2 supports the following DDL operations:
- `CREATE TABLE`
- `ALTER TABLE ADD COLUMN`
- `ALTER TABLE DROP COLUMN`
- `ALTER TABLE RENAME COLUMN`
- `ALTER TABLE ALTER COLUMN` (type changes, nullability changes)

### Basic SQL Migration Analysis

```bash
# Analyze a migration file against a base schema (JSON)
scia analyze --before base_schema.json --after migration.sql --format markdown
```

### Example Migration File

```sql
-- migration.sql
ALTER TABLE customers DROP COLUMN email;
ALTER TABLE orders ALTER COLUMN customer_id TYPE VARCHAR(50);
ALTER TABLE products ADD COLUMN description TEXT;
```

### With Warehouse Connection

Enhance SQL analysis with live dependency checking:

```bash
scia analyze \
  --before base_schema.json \
  --after migration.sql \
  --warehouse snowflake \
  --format markdown
```

This will:
1. Parse the migration SQL
2. Detect schema changes
3. Query the warehouse for downstream views/tables
4. Report impact with blast radius

---

## Live Database Comparison

Compare schemas directly from your data warehouse.

### Basic Database Comparison

```bash
scia analyze \
  --before PROD.ANALYTICS \
  --after DEV.ANALYTICS \
  --warehouse snowflake \
  --format json
```

### Cross-Database Comparison

```bash
# Compare schemas across different databases
scia analyze \
  --before PROD_DB.ANALYTICS \
  --after STAGING_DB.ANALYTICS \
  --warehouse snowflake
```

### With Custom Connection Config

```bash
scia analyze \
  --before PROD.ANALYTICS \
  --after DEV.ANALYTICS \
  --warehouse snowflake \
  --conn-file ~/my-configs/snowflake-prod.yaml
```

---

## Dependency Analysis Configuration

Control how deep SCIA analyzes transitive dependencies.

### Dependency Depth

The `--dependency-depth` flag controls how many levels of transitive dependencies to analyze:

```bash
# Shallow analysis (direct dependents only)
scia analyze \
  --before before.json \
  --after after.json \
  --warehouse snowflake \
  --dependency-depth 1

# Default analysis (3 levels)
scia analyze \
  --before before.json \
  --after after.json \
  --warehouse snowflake \
  --dependency-depth 3

# Deep analysis (up to 10 levels)
scia analyze \
  --before before.json \
  --after after.json \
  --warehouse snowflake \
  --dependency-depth 10
```

### What Dependency Depth Means

- **Depth 1**: Direct dependents only (views that directly reference changed tables)
- **Depth 2**: Direct + 1 level transitive (views that reference views that reference changed tables)
- **Depth 3** (default): Direct + 2 levels transitive
- **Depth 10** (max): Full transitive closure (all downstream dependencies)

### Performance Considerations

Higher depth values:
- ✅ More comprehensive impact analysis
- ✅ Catch cascading failures
- ❌ Slower analysis (more warehouse queries)
- ❌ May hit query limits on very large schemas

**Recommendation**: Start with depth 3, increase to 5-7 for critical production changes.

---

## Upstream & Downstream Analysis

Control which direction of dependencies to analyze.

### Downstream Only (Default)

Analyze what depends on your changes:

```bash
scia analyze \
  --before before.json \
  --after after.json \
  --warehouse snowflake \
  --no-upstream
```

### Upstream Only

Analyze what your schema depends on:

```bash
scia analyze \
  --before before.json \
  --after after.json \
  --warehouse snowflake \
  --no-downstream
```

### Both Directions (Default)

```bash
scia analyze \
  --before before.json \
  --after after.json \
  --warehouse snowflake \
  --include-upstream \
  --include-downstream
```

### Use Cases

**Downstream Analysis** (what breaks):
- Pre-deployment risk assessment
- Impact analysis for column removal
- Breaking change detection

**Upstream Analysis** (what you depend on):
- Understanding schema dependencies
- Identifying foreign key relationships
- Planning schema refactoring

---

## Connection Configuration

### Configuration File Location

SCIA looks for connection configs in this order:
1. `--conn-file` (if specified)
2. `~/.scia/{warehouse}.yaml`
3. Environment variables (future)

### Snowflake Configuration

Create `~/.scia/snowflake.yaml`:

```yaml
account: "xy12345.us-east-1.snowflakecomputing.com"
user: "your-username"
password: "your-password"
warehouse: "COMPUTE_WH"
database: "PROD_DB"
schema: "ANALYTICS"
role: "ANALYST_ROLE"
```

### Using Custom Config Files

```bash
# Use a specific config file
scia analyze \
  --before PROD.ANALYTICS \
  --after DEV.ANALYTICS \
  --warehouse snowflake \
  --conn-file ~/configs/snowflake-readonly.yaml
```

### Security Best Practices

1. **Never commit config files to git**
   ```bash
   echo "*.yaml" >> .gitignore
   ```

2. **Use read-only roles**
   ```yaml
   role: "ANALYST_READONLY"
   ```

3. **Use SSO when possible**
   ```yaml
   authenticator: "externalbrowser"
   ```

4. **Restrict file permissions**
   ```bash
   chmod 600 ~/.scia/snowflake.yaml
   ```

---

## Best Practices

### 1. Start with JSON Mode

For initial testing, use JSON mode (no warehouse connection needed):

```bash
# Export schemas to JSON first
scia analyze --before prod_schema.json --after dev_schema.json
```

### 2. Use Fail-On in CI/CD

Block deployments on high-risk changes:

```bash
# Fail pipeline if HIGH risk detected
scia analyze \
  --before PROD.ANALYTICS \
  --after migration.sql \
  --warehouse snowflake \
  --fail-on HIGH
```

### 3. Progressive Depth Analysis

Start shallow, go deeper if needed:

```bash
# Quick check (depth 1)
scia analyze --before a.json --after b.json --dependency-depth 1

# If issues found, analyze deeper
scia analyze --before a.json --after b.json --dependency-depth 5
```

### 4. Use Markdown for Reviews

Generate markdown reports for PR reviews:

```bash
scia analyze \
  --before before.json \
  --after after.json \
  --format markdown > risk_report.md
```

### 5. Combine Modes

Mix JSON and SQL for flexibility:

```bash
# Apply SQL migration to JSON base
scia analyze --before base.json --after migration.sql

# Apply SQL migration to live DB
scia analyze --before PROD.ANALYTICS --after migration.sql --warehouse snowflake
```

---

## Troubleshooting

### Connection Issues

**Error**: `Connection failed to snowflake`

**Solutions**:
1. Check config file exists: `ls ~/.scia/snowflake.yaml`
2. Verify credentials are correct
3. Test connection manually:
   ```bash
   snowsql -a your-account -u your-username
   ```
4. Use `--conn-file` to specify custom location

---

### SQL Parsing Issues

**Error**: `Failed to parse SQL in migration.sql`

**Causes**:
- Unsupported DDL (stored procedures, triggers, etc.)
- Syntax errors in SQL
- Warehouse-specific syntax not supported

**Solutions**:
1. Check which DDL operations are supported (see above)
2. SCIA will continue analysis with schema-based rules only
3. Review warnings in output

---

### Dependency Analysis Issues

**Error**: `max_depth must be 1-10, got 15`

**Solution**: Use `--dependency-depth` with value between 1 and 10

---

**Error**: `DB mode requires --warehouse flag`

**Solution**: Add `--warehouse snowflake` when using database identifiers:
```bash
scia analyze --before PROD.ANALYTICS --after DEV.ANALYTICS --warehouse snowflake
```

---

### Performance Issues

**Symptom**: Analysis takes too long

**Solutions**:
1. Reduce `--dependency-depth` (try 1 or 2)
2. Use `--no-upstream` or `--no-downstream` to skip one direction
3. Use JSON mode for offline analysis
4. Analyze specific schemas instead of entire databases

---

### Warehouse Not Implemented

**Error**: `Databricks adapter not yet implemented`

**Current Support**:
- ✅ Snowflake (fully working)
- 🏗️ Databricks (planned)
- 🏗️ PostgreSQL (planned)
- 🏗️ Redshift (planned)

**Workaround**: Export schema to JSON and use JSON mode

---

## Examples

### Example 1: Pre-Deployment Check

```bash
# Check migration before deploying to production
scia analyze \
  --before PROD.ANALYTICS \
  --after migration.sql \
  --warehouse snowflake \
  --dependency-depth 5 \
  --format markdown \
  --fail-on MEDIUM
```

### Example 2: Cross-Environment Comparison

```bash
# Compare production vs staging
scia analyze \
  --before PROD_DB.ANALYTICS \
  --after STAGING_DB.ANALYTICS \
  --warehouse snowflake \
  --format json > drift_report.json
```

### Example 3: Offline Analysis

```bash
# Export schemas first
# (use your warehouse's export tool)

# Then analyze offline
scia analyze \
  --before prod_export.json \
  --after dev_export.json \
  --format markdown
```

### Example 4: CI/CD Integration

```yaml
# GitHub Actions example
- name: Schema Risk Analysis
  run: |
    scia analyze \
      --before ${{ github.base_ref }}.json \
      --after ${{ github.head_ref }}.json \
      --fail-on HIGH \
      --format markdown > risk_report.md
    
- name: Comment PR with Report
  uses: actions/github-script@v6
  with:
    script: |
      const fs = require('fs');
      const report = fs.readFileSync('risk_report.md', 'utf8');
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: report
      });
```

---

## Next Steps

- Review the [main README](../README.md) for basic usage
- Check [CHANGELOG.md](../CHANGELOG.md) for version history
- See [implementation plan](requirements/roadmap/plan_scia_roadmap_v02.md) for roadmap

---

**Questions or Issues?** Check the main documentation or file an issue on GitHub.
