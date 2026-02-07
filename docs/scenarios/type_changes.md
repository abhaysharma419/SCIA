# Scenario: Type Changes

Changing the data type of a column (e.g., from `INTEGER` to `VARCHAR`) can cause subtle but critical failures.

## Risks (40-60)

1. **Casting Errors**: Downstream queries that perform arithmetic or specific functions (e.g., `SUM(price)`) will fail if a numeric column is changed to a string.
2. **Buffer Overflows**: Changing from a larger type to a smaller type (e.g., `VARCHAR(255)` to `VARCHAR(10)`) will cause data truncation or insertion errors.
3. **Index Invalidation**: In some databases, changing the type requires rebuilding indexes, which can cause significant performance degradation during the change.

## SCIA Detection

SCIA flags any change where the `data_type` property of a column differs between versions.

### Example Finding

```json
{
  "finding_type": "COLUMN_TYPE_CHANGED",
  "severity": "MEDIUM",
  "base_risk": 40,
  "evidence": {
    "table": "orders",
    "column": "total",
    "before": "FLOAT",
    "after": "VARCHAR"
  },
  "description": "Column 'total' type changed from FLOAT to VARCHAR."
}
```

## Mitigation Strategies

- **Implicit Compatibility**: Ensure the new type is compatible with existing data (e.g., all current values can be cast to the new type).
- **Secondary Columns**: Create a new column with the target type, sync data, and then switch applications to use the new column before dropping the old one.
