# Scenario: Column Removal

Removing a column is one of the most dangerous schema changes because of its wide-reaching impact on downstream systems.

## Why it is High Risk (80+)

1. **Downstream Views**: Any view that references the removed column (e.g., `SELECT email FROM users`) will immediately fail with a "Column not found" error.
2. **Join Keys**: If the column is used as a join key (e.g., `JOIN orders ON users.id = orders.user_id`), any query performing that join will break.
3. **Application Failures**: ORMs or hardcoded queries in application code will fail if they expect the column to exist.
4. **Data Loss**: Once a column is dropped from a table, its data is permanently deleted unless a backup exists.

## SCIA Detection

SCIA detects column removal by comparing the "Before" and "After" schemas.

### Example Finding

```json
{
  "finding_type": "COLUMN_REMOVED",
  "severity": "HIGH",
  "base_risk": 80,
  "evidence": {"table": "customers", "column": "email"},
  "description": "Column 'email' removed from table 'customers'."
}
```

## Mitigation Strategies

- **Phase 1: Deprecation**: Mark the column as deprecated in documentation/code.
- **Phase 2: Nullable/Default**: If possible, make the column nullable instead of removing it immediately.
- **Phase 3: Impact Analysis**: Use SCIA's `--warehouse snowflake` mode to find all downstream views depending on this column before dropping it.
