# SCIA Risk Scenarios

This directory contains detailed explanations of the risk scenarios analyzed by SCIA.

## 🔴 Breaking Changes (High Risk)

Breaking changes are those that will immediately cause downstream queries or applications to fail.

- **[Column Removal](./column_removal.md)**: Removing a column used in views or join keys.
- **[Table Removal](./table_removal.md)**: Removing an entire table.
- **[Join Key Change](./join_key_change.md)**: Changing the type or removing a column used in a JOIN.

## 🟡 Data Quality & Compatibility (Medium Risk)

These changes might not break everything immediately but can lead to data loss, casting errors, or incorrect results.

- **[Type Changes](./type_changes.md)**: Changing column data types (e.g., INT to STRING).
- **[Nullability Changes](./nullability_changes.md)**: Changing a column from NULL to NOT NULL.
- **[Grain Change](./grain_change.md)**: Removing a column used in GROUP BY clauses.

## 🟢 Safe Changes (Low Risk)

- **[Column Addition](./column_addition.md)**: Adding a new nullable column.
- **[Table Addition](./table_addition.md)**: Adding a new table.
