# SCIA Requirements Document v0.2

**Status:** Active  
**Last Updated:** January 27, 2026  
**Version:** 0.2 (Extended with DB Support & Impact Analysis)

---

## 1. Executive Summary

SCIA (Schema Change Impact Analyzer) is a **deterministic, rule-based schema change risk assessment tool** designed to:

1. **Detect structural schema changes** (column additions, removals, type changes, nullability changes)
2. **Quantify impact risk** using deterministic scoring (LOW < 30, MEDIUM 30–69, HIGH ≥ 70)
3. **Analyze downstream/upstream dependencies** by querying Snowflake metadata
4. **Support multiple input sources** (JSON exports, SQL migrations, live database connections)
5. **Be extensible** to support multiple data warehouses (Snowflake, Databricks, PostgreSQL, Redshift, etc.)

---

## 2. Core Principles

✅ **Determinism**: Same input → same output, always.  
✅ **Trust**: Correctness over feature completeness.  
✅ **Local execution**: No SaaS, no cloud dependencies.  
✅ **Read-only**: Never modifies schemas or data.  
✅ **Graceful degradation**: Missing signals don't cause failures.  
✅ **Extensibility**: Add warehouses without core logic changes.  

---

## 3. Functional Requirements

### 3.1 Schema Change Detection (v0.1 — Complete)

#### Supported Changes
- ✅ Column addition
- ✅ Column removal
- ✅ Data type changes
- ✅ Nullability changes

#### Input Sources (v0.1)
- ✅ JSON schema exports

#### Output
- ✅ Raw diffs (internal representation)
- ✅ Risk-scored findings
- ✅ Deterministic risk classification

---

### 3.2 Extended Input Sources (v0.2 — New)

SCIA must accept schema definitions from **three distinct sources**:

#### 3.2.1 JSON Export (Current)

```bash
scia analyze --before before.json --after after.json
```

**Input format:** Pre-exported JSON containing `TableSchema` objects.

**Use case:** Offline analysis, version control integration, CI/CD pipelines.

---

#### 3.2.2 SQL Migration Files

```bash
scia analyze \
  --before ANALYTICS \
  --after migration.sql \
  --warehouse snowflake \
  --conn-file ~/.snowflake/config.json
```

**Input format:** DDL statements (CREATE, ALTER, DROP).

**Supported statements:**
- `CREATE TABLE schema.table (col1 TYPE, ...)`
- `ALTER TABLE schema.table ADD COLUMN col_name TYPE`
- `ALTER TABLE schema.table DROP COLUMN col_name`
- `ALTER TABLE schema.table MODIFY COLUMN col_name NEW_TYPE`
- `ALTER TABLE schema.table RENAME COLUMN old_name TO new_name`

**Before state:** Fetched from live warehouse.

**After state:** Inferred from DDL parsing.

**Use case:** Pre-deployment risk assessment for migrations.

---

#### 3.2.3 Live Database Connection

```bash
# Single schema
scia analyze \
  --before DEV.ANALYTICS \
  --after PROD.ANALYTICS \
  --warehouse snowflake \
  --conn-file ~/.snowflake/config.json

# Multiple tables
scia analyze \
  --before SCHEMA_NAME \
  --after SCHEMA_NAME_NEW \
  --warehouse snowflake
```

**Before/After sources:** Both from live warehouse.

**Use case:** Comparing dev/staging/prod environments, post-deployment validation.

---

### 3.3 Dependency Graph & Impact Analysis (v0.2 — New)

When using **live database connections**, SCIA must analyze **downstream and upstream impacts**.

#### 3.3.1 Downstream Dependencies

**Definition:** Tables and views that **consume data** from changed tables.

**Detection mechanism:**
- Query `information_schema.view_definition` for view dependencies
- Parse view SELECT statements to identify table references
- Identify foreign key constraints (if available)
- Identify application views/materialized views

**Risks assessed:**
- Will downstream views break if column is removed?
- Will downstream queries fail if column type changes?
- Will downstream applications see NULL where they expect values?

**Output:**
```json
{
  "finding_type": "COLUMN_REMOVED",
  "downstream_impact": [
    {
      "type": "VIEW",
      "name": "ANALYTICS.DAILY_REVENUE",
      "objects_affected": 1,
      "risk_level": "HIGH",
      "reason": "View selects removed column CUSTOMER_ID"
    },
    {
      "type": "MATERIALIZED_VIEW",
      "name": "WAREHOUSE.ORDERS_MV",
      "objects_affected": 1,
      "risk_level": "MEDIUM"
    }
  ]
}
```

#### 3.3.2 Upstream Dependencies

**Definition:** Tables and views that **provide data** to changed tables.

**Detection mechanism:**
- Query `information_schema.table_constraints` for foreign keys
- Parse stored procedures/functions that write to the table
- Identify ETL processes (if metadata available)

**Risks assessed:**
- Will INSERT/UPDATE operations fail if nullability changes?
- Will foreign key constraints break?
- Will upstream ETL pipelines need reconfiguration?

---

### 3.4 Warehouse Abstraction (Extensibility)

To support **Snowflake, Databricks, PostgreSQL, Redshift**, SCIA must use a **plugin-based warehouse adapter pattern**.

#### 3.4.1 Warehouse Adapter Interface

```python
# filepath: scia/warehouse/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from scia.models.schema import TableSchema, ColumnSchema

class WarehouseAdapter(ABC):
    """
    Abstract base for warehouse implementations.
    Each warehouse (Snowflake, Databricks, etc.) provides concrete implementation.
    """
    
    @abstractmethod
    def connect(self, config_path: str) -> None:
        """Establish read-only connection."""
        pass
    
    @abstractmethod
    def fetch_schema(self, database: str, schema: str) -> List[TableSchema]:
        """
        Fetch table and column metadata.
        
        Returns: List[TableSchema]
        """
        pass
    
    @abstractmethod
    def fetch_views(self, database: str, schema: str) -> List[Dict]:
        """
        Fetch view definitions.
        
        Returns: [
          {
            "view_name": "MY_VIEW",
            "view_definition": "SELECT ... FROM ...",
            "is_materialized": False
          }
        ]
        """
        pass
    
    @abstractmethod
    def fetch_foreign_keys(self, database: str, schema: str) -> List[Dict]:
        """
        Fetch foreign key relationships.
        
        Returns: [
          {
            "table": "ORDERS",
            "column": "CUSTOMER_ID",
            "referenced_table": "CUSTOMERS",
            "referenced_column": "ID"
          }
        ]
        """
        pass
    
    @abstractmethod
    def fetch_procedures(self, database: str, schema: str) -> List[Dict]:
        """
        Fetch stored procedure definitions (if available).
        
        Some warehouses may not support this.
        """
        pass
    
    @abstractmethod
    def parse_table_references(self, sql: str) -> List[str]:
        """
        Parse SQL and extract table references.
        
        Returns: ["TABLE1", "TABLE2", ...]
        """
        pass
```

#### 3.4.2 Concrete Implementations

**Snowflake (v0.2):**
```python
# filepath: scia/warehouse/snowflake.py

class SnowflakeAdapter(WarehouseAdapter):
    def connect(self, config_path: str):
        # Load ~/.snowflake/config.json or provided path
        # Use snowflake.connector (read-only role)
        pass
    
    def fetch_schema(self, database: str, schema: str):
        # Query: information_schema.columns
        # Return normalized TableSchema objects
        pass
    
    def fetch_views(self, database: str, schema: str):
        # Query: information_schema.views
        # Extract view_definition
        pass
    
    def fetch_foreign_keys(self, database: str, schema: str):
        # Query: information_schema.table_constraints
        pass
    
    def parse_table_references(self, sql: str):
        # Use regex or sqlparse to extract table names
        pass
```

**Databricks (Future):**
```python
# filepath: scia/warehouse/databricks.py

class DatabricksAdapter(WarehouseAdapter):
    # Implementation differs in auth, system tables, and syntax
    # Use INFORMATION_SCHEMA from Unity Catalog
    pass
```

**PostgreSQL (Future):**
```python
# filepath: scia/warehouse/postgres.py

class PostgresAdapter(WarehouseAdapter):
    # Query: information_schema.columns, information_schema.views
    # Use psycopg2 or equivalent
    pass
```

**Redshift (Future):**
```python
# filepath: scia/warehouse/redshift.py

class RedshiftAdapter(WarehouseAdapter):
    # Similar to Postgres but with Redshift-specific metadata
    pass
```

#### 3.4.3 Adapter Registry

```python
# filepath: scia/warehouse/__init__.py

from scia.warehouse.base import WarehouseAdapter
from scia.warehouse.snowflake import SnowflakeAdapter

WAREHOUSE_ADAPTERS = {
    'snowflake': SnowflakeAdapter,
    'databricks': None,  # Future
    'postgres': None,     # Future
    'redshift': None      # Future
}

def get_adapter(warehouse_type: str) -> WarehouseAdapter:
    """Factory function to get adapter instance."""
    adapter_class = WAREHOUSE_ADAPTERS.get(warehouse_type.lower())
    if not adapter_class:
        raise ValueError(f"Unsupported warehouse: {warehouse_type}")
    return adapter_class()
```

---

### 3.5 Impact Scorer (New Component)

#### 3.5.1 Responsibilities

Given a schema change, determine:
1. **Direct impact**: How many downstream objects are affected?
2. **Blast radius**: How deep does impact propagate?
3. **Business risk**: Are critical tables/views affected?

#### 3.5.2 Algorithm

```
For each finding (e.g., COLUMN_REMOVED):
  1. Identify affected table
  2. Query dependency graph:
     - Direct dependents (views, tables that reference this column)
     - Transitive dependents (tables that depend on dependents)
  3. Count affected objects
  4. Apply risk multiplier:
     - HIGH if critical table (flagged in config)
     - MEDIUM if upstream ETL affected
     - LOW if few dependents
  5. Return impact details
```

#### 3.5.3 Output Format

```json
{
  "finding_type": "COLUMN_REMOVED",
  "table": "ORDERS",
  "column": "CUSTOMER_ID",
  "base_risk": 80,
  "downstream_impact": {
    "direct_dependents": 3,
    "transitive_dependents": 5,
    "critical_objects": [
      "ANALYTICS.REVENUE_VIEW",
      "REPORTING.DAILY_DASHBOARD"
    ],
    "affected_applications": [
      "bi_tool_tableau",
      "data_export_pipeline"
    ]
  }
}
```

---

## 4. Scenario Breakdown

### Scenario 1: Offline JSON Analysis (v0.1)

```bash
scia analyze --before before.json --after after.json --format json
```

**Input:**
- Two JSON files with pre-exported schemas

**Flow:**
1. Load JSON files
2. Compute diff
3. Apply rules
4. Aggregate risk
5. Output JSON

**Exit code:** 0 if LOW/MEDIUM, 1 if HIGH

**Use case:** PR analysis, version control integration

---

### Scenario 2: Pre-Deployment SQL Review (v0.2)

```bash
scia analyze \
  --before ANALYTICS \
  --after migration.sql \
  --warehouse snowflake \
  --conn-file ~/.snowflake/config.json \
  --format markdown
```

**Input:**
- Before: Live schema from Snowflake (`ANALYTICS`)
- After: Parsed DDL from `migration.sql`

**Flow:**
1. Connect to Snowflake
2. Fetch current schema for `ANALYTICS`
3. Parse DDL from migration.sql
4. Compute diff
5. Analyze downstream dependencies
6. Output markdown report

**Output example:**
```markdown
# SCIA Impact Report
**Risk Score:** 85
**Classification:** HIGH

## Changes Detected
- Column `CUSTOMER_ID` removed from `ORDERS`
- 3 downstream views affected
- 1 critical application impacted

## Recommendations
- Review views: ANALYTICS.REVENUE_VIEW
- Update BI pipeline before deployment
```

**Exit code:** 1 (HIGH risk)

---

### Scenario 3: Dev vs. Prod Comparison (v0.2)

```bash
scia analyze \
  --before DEV.ANALYTICS \
  --after PROD.ANALYTICS \
  --warehouse snowflake \
  --conn-file ~/.snowflake/config.json
```

**Input:**
- Before: Live schema from DEV environment
- After: Live schema from PROD environment

**Flow:**
1. Connect to Snowflake
2. Fetch schemas from both environments
3. Compute diff
4. Analyze dependencies in PROD
5. Output findings

**Use case:** Detect schema drift, validate deployments

---

### Scenario 4: Multi-Warehouse Support (Future)

```bash
# Databricks
scia analyze \
  --before PROD.ANALYTICS \
  --after migration.sql \
  --warehouse databricks \
  --conn-file ~/.databricks/config.json

# PostgreSQL
scia analyze \
  --before public.orders \
  --after migration.sql \
  --warehouse postgres \
  --conn-string "postgresql://user:pass@localhost/mydb"
```

**Key design:** Zero changes to core logic. Just switch adapter.

---

## 5. Non-Functional Requirements

### 5.1 Performance

- Schema fetch: < 5 seconds for 100 tables
- Diff computation: < 1 second
- Dependency analysis: < 10 seconds for complex graphs
- Total runtime: < 20 seconds for typical use case

### 5.2 Reliability

- Graceful degradation if metadata unavailable
- Retry logic for transient connection failures
- Clear error messages for configuration issues
- Logging for debugging

### 5.3 Security

- Read-only connections only
- No credentials in logs
- Support for ~/.config/warehouse-name/credentials
- Respect warehouse RBAC

### 5.4 Maintainability

- Plugin interface for new warehouses
- Comprehensive test coverage
- Clear separation of concerns
- No circular dependencies

---

## 6. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI (main.py)                        │
│  analyze, diff, config commands                              │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                  Input Resolver                              │
│  Determines input type (JSON, SQL, DB identifier)            │
└────────────────┬────────────────────────────────────────────┘
                 │
      ┌──────────┼──────────┐
      │          │          │
   JSON      SQL Parser  Warehouse
  Loader     (DDL)       Adapter
      │          │          │
      └──────────┼──────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                  Schema Objects                              │
│  TableSchema, ColumnSchema                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                  Diff Engine (diff.py)                       │
│  Compares before/after schemas                               │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                   Rules Engine (rules.py)                    │
│  Applies deterministic rules to diffs                        │
│  Emits: Finding objects                                      │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│          Impact Analyzer (NEW — impact.py)                   │
│  Enriches findings with downstream/upstream dependencies     │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                Risk Aggregator (risk.py)                     │
│  Sums base_risk, classifies overall risk                     │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                 Output Renderers                             │
│  JSON (json.py) + Markdown (markdown.py)                     │
└────────────────┬────────────────────────────────────────────┘
                 │
             (to stdout)
```

---

## 7. Data Models

### 7.1 Core Models (Existing)

```python
@dataclass
class ColumnSchema:
    schema_name: str
    table_name: str
    column_name: str
    data_type: str
    is_nullable: bool
    ordinal_position: int

@dataclass
class TableSchema:
    schema_name: str
    table_name: str
    columns: List[ColumnSchema]

class FindingType(Enum):
    COLUMN_ADDED = "COLUMN_ADDED"
    COLUMN_REMOVED = "COLUMN_REMOVED"
    COLUMN_TYPE_CHANGED = "COLUMN_TYPE_CHANGED"
    COLUMN_NULLABILITY_CHANGED = "COLUMN_NULLABILITY_CHANGED"

class Severity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

@dataclass
class Finding:
    finding_type: FindingType
    severity: Severity
    base_risk: int  # 0-100
    evidence: Dict  # proof of change
    confidence: float = 1.0
    description: str = ""
```

### 7.2 New Models (v0.2)

```python
@dataclass
class DependencyObject:
    """Represents a downstream/upstream object."""
    object_type: str  # VIEW, MATERIALIZED_VIEW, FUNCTION, PROCEDURE
    name: str
    schema: str
    is_critical: bool = False
    description: str = ""

@dataclass
class ImpactDetail:
    """Enrichment for a Finding with dependency analysis."""
    direct_dependents: List[DependencyObject]
    transitive_dependents: List[DependencyObject]
    affected_applications: List[str]
    estimated_blast_radius: int  # number of affected objects

@dataclass
class EnrichedFinding(Finding):
    """Finding + impact analysis."""
    impact_detail: Optional[ImpactDetail] = None

@dataclass
class AnalysisResult:
    """Output of analyze()."""
    risk_score: int
    classification: str  # LOW, MEDIUM, HIGH
    findings: List[EnrichedFinding]
    metadata: Dict  # input sources, warehouse, timestamps, etc.
```

---

## 8. Configuration & Extensibility

### 8.1 Connection Configuration

**Location:** `~/.scia/config.yaml` or `~/.warehouse-name/credentials`

```yaml
# ~/.scia/snowflake.yaml
warehouse: snowflake
account: xy12345.us-east-1
user: analyst_ro
role: ANALYST_READ_ONLY
database: ANALYTICS
warehouse: COMPUTE_WH
```

### 8.2 Adding a New Warehouse

**Steps:**
1. Create `scia/warehouse/my_warehouse.py`
2. Implement `WarehouseAdapter` interface
3. Register in `scia/warehouse/__init__.py`
4. Add tests in `tests/test_warehouse_my_warehouse.py`
5. Update CLI help text

**Example:**
```python
# scia/warehouse/my_warehouse.py

from scia.warehouse.base import WarehouseAdapter

class MyWarehouseAdapter(WarehouseAdapter):
    def connect(self, config_path: str):
        # Implementation
        pass
    
    def fetch_schema(self, database: str, schema: str):
        # Implementation
        pass
    
    # ... rest of interface
```

```python
# scia/warehouse/__init__.py

from scia.warehouse.my_warehouse import MyWarehouseAdapter

WAREHOUSE_ADAPTERS = {
    'snowflake': SnowflakeAdapter,
    'my_warehouse': MyWarehouseAdapter,  # Add here
}
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

- Diff engine (existing: `test_diff.py`)
- Rules engine (mock findings)
- Risk aggregator
- SQL parser (DDL variations)
- Impact analyzer (dependency resolution)

### 9.2 Integration Tests

- End-to-end with test Snowflake instance (if available)
- JSON → JSON pipeline
- SQL file parsing → impact analysis
- Warehouse adapter interface compliance

### 9.3 Edge Cases

- Missing columns in views
- Circular dependencies
- Deep dependency graphs (10+ levels)
- Views with complex JOINs
- Non-standard table references (quoted names, special characters)
- Graceful failure on metadata unavailable

---

## 10. Implementation Roadmap

### Phase 1 (v0.1 — Complete)
- ✅ Schema diff engine
- ✅ Deterministic rules
- ✅ Risk aggregation
- ✅ JSON output
- ✅ CLI interface

### Phase 2 (v0.2 — Proposed)
- [ ] SQL DDL parsing and inference
- [ ] Live database connection (Snowflake)
- [ ] Warehouse adapter abstraction
- [ ] Dependency graph analysis
- [ ] Impact scoring
- [ ] Enhanced JSON output with dependencies

### Phase 3 (v0.3+ — Future)
- [ ] Databricks adapter
- [ ] PostgreSQL adapter
- [ ] Redshift adapter
- [ ] Application registry (external apps affected)
- [ ] Change approval workflow
- [ ] Historical impact tracking

---

## 11. Acceptance Criteria

### 11.1 v0.2 Completion

- [ ] SQL file parsing works for CREATE/ALTER DDL
- [ ] Live DB connection fetches schema correctly
- [ ] Dependency graph analysis detects downstream views
- [ ] Impact scores reflect blast radius
- [ ] Warehouse adapter interface is clean and testable
- [ ] Documentation shows how to add new warehouses
- [ ] Exit codes respect --fail-on flag
- [ ] Graceful degradation on metadata errors
- [ ] All v0.1 tests still pass

### 11.2 Warehouse Extensibility

- [ ] Adapter interface is well-defined
- [ ] Adding new warehouse requires < 500 lines of code
- [ ] No changes to core logic needed
- [ ] Registry pattern supports loading adapters dynamically

---

## 12. Risk Mitigation

### 12.1 False Positives

**Risk:** Over-reporting impact (e.g., flagging harmless changes as HIGH).

**Mitigation:**
- Use explicit evidence thresholds
- Require metadata confirmation
- Provide confidence scores

### 12.2 Missing Dependencies

**Risk:** Analyzing complex schemas where metadata is incomplete.

**Mitigation:**
- Graceful degradation (assume no dependents if metadata unavailable)
- Clear logging of missing signals
- Option to ignore warehouses

### 12.3 Performance

**Risk:** Dependency analysis on large schemas (1000+ tables) becomes slow.

**Mitigation:**
- Lazy-load dependency graph
- Cache results (opt-in)
- Limit transitive depth (e.g., max 5 levels)

---

## 13. References & Links

- **Design Document:** [design.md](design.md)
- **Coding Instructions:** [coding_agent_instructions.md](coding_agent_instructions.md)
- **README:** [README.md](README.md)

---

## 14. Approval & Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| Author | Engineering Team | 2026-01-27 | Draft |
| Reviewer | (Pending) | — | Pending |
| Approved By | (Pending) | — | Pending |

---

## Appendix A: CLI Reference (Extended)

```bash
# v0.1 (JSON only)
scia analyze --before before.json --after after.json

# v0.2 (Multiple sources)
scia analyze \
  --before ANALYTICS \
  --after migration.sql \
  --warehouse snowflake \
  --conn-file ~/.snowflake/config.json \
  --format json \
  --fail-on HIGH

scia analyze \
  --before DEV.ANALYTICS \
  --after PROD.ANALYTICS \
  --warehouse snowflake

# Future (other warehouses)
scia analyze \
  --before analytics \
  --after migration.sql \
  --warehouse databricks \
  --conn-file ~/.databricks/config.json
```

---

## Appendix B: Example Output (v0.2 with Impact)

```json
{
  "risk_score": 85,
  "classification": "HIGH",
  "findings": [
    {
      "finding_type": "COLUMN_REMOVED",
      "severity": "HIGH",
      "base_risk": 80,
      "evidence": {
        "table": "ORDERS",
        "column": "CUSTOMER_ID",
        "change": "removed"
      },
      "confidence": 1.0,
      "description": "Column 'CUSTOMER_ID' was removed from table 'ORDERS'.",
      "impact_detail": {
        "direct_dependents": [
          {
            "object_type": "VIEW",
            "name": "ANALYTICS.DAILY_REVENUE",
            "schema": "ANALYTICS",
            "is_critical": true,
            "description": "View depends on CUSTOMER_ID for grouping"
          },
          {
            "object_type": "VIEW",
            "name": "ANALYTICS.CUSTOMER_SUMMARY",
            "schema": "ANALYTICS",
            "is_critical": true
          }
        ],
        "transitive_dependents": [
          {
            "object_type": "MATERIALIZED_VIEW",
            "name": "WAREHOUSE.ORDERS_MV",
            "schema": "WAREHOUSE"
          }
        ],
        "affected_applications": [
          "tableau_dashboard_revenue",
          "looker_explore_customers",
          "python_etl_pipeline_v2"
        ],
        "estimated_blast_radius": 5
      }
    }
  ],
  "metadata": {
    "before_source": {
      "type": "db",
      "warehouse": "snowflake",
      "database": "PROD",
      "schema": "ANALYTICS"
    },
    "after_source": {
      "type": "sql",
      "file": "migration.sql"
    },
    "timestamp": "2026-01-27T14:32:00Z",
    "execution_time_ms": 5234
  }
}
```

---

**End of Document**
