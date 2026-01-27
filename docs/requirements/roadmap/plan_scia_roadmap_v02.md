# Plan: SCIA v0.1→v0.2 Phased Implementation (Final)

**TL;DR**: Execute in strict sequence: (1) Complete v0.1 to production-ready, (2) Design v0.2 warehouse/parser abstractions, (3) Build v0.2 SQL & dependency features with full test coverage, (4) Harden CLI. Snowflake fully working; others designed as stubs. Est. 10-14 weeks across 4 phases.

---

## Phase 0: Complete v0.1 to Production Ready — **Weeks 1–3**

### Objective
Ship v0.1 with complete test coverage, stable CLI, documented exit codes. Gate all Phase 1 work on this passing.

### Steps

1. **Consolidate & Expand Unit Tests** → Create `tests/conftest.py` with reusable Pydantic fixtures (`ColumnSchema`, `TableSchema`, `Finding`, `SchemaDiff`). Expand `tests/test_diff.py` to 8 tests (no-op, add col, remove col, type change, nullability change, table add, table remove, multiple changes). Create `tests/test_rules.py` with 9 tests (3 rules × 3 scenarios each: applies correctly, skips non-matching, aggregates multiple). Create `tests/test_risk.py` with 4 tests (LOW <30, MEDIUM 30–69, HIGH ≥70, boundary cases).

2. **Integration Test Suite** → Create `tests/integration/test_cli.py` with 8 tests: JSON input/output, Markdown output, missing file error (exit 1), invalid JSON error (exit 1), `--fail-on HIGH/MEDIUM/LOW` behavior, `--format` flag validation, empty schema (no changes, exit 0), multiple findings aggregation.

3. **Test Pipeline Analysis** → Create `tests/test_analyze.py` with 5 tests: diff → rules pipeline, multiple findings combined, risk scoring integration, graceful SQL degradation (SQL parsing fails, analysis continues), optional `sql_signals` parameter (None and Dict paths).

4. **Snowflake Adapter (Offline)** → Create `tests/test_snowflake_adapter.py` with 6 mocked tests: connection success, connection failure (graceful), schema fetch success, schema fetch with missing metadata (empty return), view fetch success, foreign key fetch (stub for v0.2). **NO live warehouse calls.**

5. **Coverage Gate** → Run `pytest --cov=scia --cov-report=term-missing`. Target >90% coverage. Fix any gaps. Document any intentional exclusions (e.g., debug logging).

6. **CLI Documentation** → Update `README.md` with v0.1 final state:
   - Usage: `scia analyze --before <json> --after <json> [--format json|markdown] [--fail-on HIGH|MEDIUM|LOW]`
   - Exit codes: `0` = below threshold, `1` = at/above threshold or error
   - Output examples (JSON + Markdown)
   - Note: "v0.2 will extend with SQL migrations, live DB, and warehouse support."

7. **Version Bump** → Update `pyproject.toml` version to `0.1.0` (or next patch if already released). Tag as `v0.1-final` in git.

### Validation Checklist

- [ ] All tests pass locally (`pytest` with no flags)
- [ ] Coverage report shows >90% (or document exclusions)
- [ ] CLI works: `scia analyze --before tests/fixtures/before.json --after tests/fixtures/after.json` produces expected JSON
- [ ] Exit codes verified: `scia ... --fail-on HIGH` returns 1 on HIGH findings
- [ ] README updated with v0.1 examples
- [ ] No warnings or deprecations in test output

---

## Phase 1: v0.2 Architecture & Abstractions — **Weeks 4–7**

### Objective
Design extensible warehouse system, SQL parsing, input resolution. **All components unit-tested, no implementation of Phase 2 logic yet.**

### Steps

1. **Warehouse Abstraction Layer** → Create `scia/warehouse/base.py`:
   ```python
   class WarehouseAdapter(ABC):
       @abstractmethod
       def connect(self, config: Dict[str, Any]) -> None: pass
       @abstractmethod
       def fetch_schema(self, database: str, schema: str) -> List[TableSchema]: pass
       @abstractmethod
       def fetch_views(self, database: str, schema: str) -> List[Dict]: pass
       @abstractmethod
       def fetch_foreign_keys(self, database: str, schema: str) -> List[Dict]: pass
       @abstractmethod
       def parse_table_references(self, sql: str) -> List[str]: pass
   ```
   Create `tests/warehouse/test_warehouse_abstraction.py` verifying all methods are abstract.

2. **Snowflake Adapter (Refactored)** → Move/refactor `scia/metadata/snowflake.py` → `scia/warehouse/snowflake.py` implementing full `WarehouseAdapter` interface. **Keep existing `fetch_schema()`, `fetch_views()`, add `fetch_foreign_keys()` (returns empty for now—full impl in Phase 2), `parse_table_references()` (uses sqlglot, already in `scia/sql/parser.py`). Create `tests/warehouse/test_snowflake_adapter.py` with 8 mocked tests (existing 6 + new foreign key mock + parse_table_references mock).

3. **Warehouse Adapter Registry** → Create `scia/warehouse/__init__.py`:
   ```python
   WAREHOUSE_ADAPTERS = {
       'snowflake': SnowflakeAdapter,
       'databricks': None,    # Stub: raise NotImplementedError
       'postgres': None,      # Stub: raise NotImplementedError
       'redshift': None       # Stub: raise NotImplementedError
   }
   def get_adapter(warehouse_type: str) -> WarehouseAdapter:
       if warehouse_type.lower() not in WAREHOUSE_ADAPTERS:
           raise ValueError(f"Unsupported warehouse: {warehouse_type}")
       adapter_class = WAREHOUSE_ADAPTERS[warehouse_type.lower()]
       if adapter_class is None:
           raise NotImplementedError(f"{warehouse_type} adapter not yet implemented")
       return adapter_class()
   ```
   Create `tests/warehouse/test_adapter_registry.py` with 4 tests: get Snowflake (success), get unsupported warehouse (ValueError), get Databricks (NotImplementedError), all stubs raise NotImplementedError.

4. **Warehouse Stub Implementations** → Create `scia/warehouse/databricks.py`, `scia/warehouse/postgres.py`, `scia/warehouse/redshift.py` with skeleton classes that inherit `WarehouseAdapter` but raise `NotImplementedError` in all methods. Include docstrings explaining what each would do (see v0.2 requirements). **No actual implementation.**

5. **SQL DDL Parser** → Create `scia/sql/ddl_parser.py` with function:
   ```python
   def parse_ddl_to_schema(ddl_sql: str) -> List[TableSchema]:
       """Parse CREATE TABLE, ALTER TABLE DDL and return normalized schema.
       Supports: CREATE TABLE, ALTER ADD/DROP/MODIFY/RENAME COLUMN.
       Gracefully ignores unsupported statements."""
   ```
   Create `tests/test_ddl_parser.py` with 8 unit tests:
   - CREATE TABLE (simple, multi-column)
   - ALTER ADD COLUMN
   - ALTER DROP COLUMN
   - ALTER MODIFY COLUMN (type change)
   - ALTER RENAME COLUMN
   - Multiple statements in one string
   - Graceful handling of unsupported DDL (stored procedures, constraints—ignored, warn)
   - Edge cases (quoted identifiers, special chars, Snowflake syntax)

6. **Input Resolver** → Create `scia/input/resolver.py`:
   ```python
   class InputType(Enum):
       JSON = "json"
       SQL = "sql"
       DATABASE = "database"
   
   def resolve_input(before: str, after: str, warehouse: Optional[str] = None) -> Tuple[InputType, Dict]:
       """Detect input mode and return metadata.
       - *.json → JSON mode (before: schema list, after: schema list)
       - *.sql → SQL mode (before: schema from warehouse, after: parsed DDL)
       - SCHEMA.TABLE → Database mode (both from warehouse)
       Returns: (InputType, {'before_source': ..., 'after_source': ...})"""
   ```
   Create `tests/test_input_resolver.py` with 6 tests: JSON detection, SQL detection, DB identifier detection, invalid input (no extension), ambiguous input (both .json and .sql), error on DB mode without warehouse specified.

7. **Connection Config Manager** → Create `scia/config/connection.py`:
   ```python
   def load_connection_config(warehouse: str, conn_file: Optional[str] = None) -> Dict[str, Any]:
       """Load warehouse connection config.
       Priority: --conn-file > ~/.scia/{warehouse}.yaml > defaults
       """
   ```
   Create `tests/config/test_connection.py` with 4 tests: load from file, load from default path, file override, missing file (graceful).

8. **Extended Data Models** → Update `scia/models/finding.py`:
   ```python
   class DependencyObject(BaseModel):
       object_type: str  # VIEW, MATERIALIZED_VIEW, FUNCTION, PROCEDURE
       name: str
       schema: str
       is_critical: bool = False
   
   class ImpactDetail(BaseModel):
       direct_dependents: List[DependencyObject] = []
       transitive_dependents: List[DependencyObject] = []
       affected_applications: List[str] = []
       estimated_blast_radius: int = 0
   
   class EnrichedFinding(Finding):
       impact_detail: Optional[ImpactDetail] = None
   ```
   Create `tests/models/test_extended_models.py` with 3 tests: DependencyObject validation, ImpactDetail aggregation, EnrichedFinding serialization.

### Validation Checklist

- [ ] `get_adapter('snowflake')` works; others raise NotImplementedError
- [ ] `parse_ddl_to_schema("CREATE TABLE ...")` returns `List[TableSchema]`
- [ ] `resolve_input('before.json', 'after.json')` returns `InputType.JSON`
- [ ] `resolve_input('PROD.ANALYTICS', 'DEV.ANALYTICS', 'snowflake')` returns `InputType.DATABASE`
- [ ] All unit tests pass (>90% coverage for new code)
- [ ] No breaking changes to v0.1 models or CLI

---

## Phase 2: v0.2 SQL & Dependency Features — **Weeks 8–11**

### Objective
Integrate SQL parsing, dependency analysis, extend rules. Implement full v0.2 feature set with comprehensive test coverage.

### Steps

1. **SQL-Based Rules** → Update `scia/core/rules.py`:
   - Implement `rule_join_key_changed(diff: SchemaDiff, sql_signals: Optional[Dict] = None) -> List[Finding]`: If column used in JOIN and changed/removed, emit HIGH severity finding with evidence showing JOIN clause.
   - Implement `rule_grain_change(diff: SchemaDiff, sql_signals: Optional[Dict] = None) -> List[Finding]`: If column in GROUP BY removed, emit MEDIUM severity.
   - Implement `rule_potential_breakage(diff: SchemaDiff, sql_signals: Optional[Dict] = None) -> List[Finding]`: Catch-all for complex changes (e.g., type change on numeric column). MEDIUM severity.
   - Update `ALL_RULES` list to include new rules.
   - Extend `tests/test_rules.py` with 9 new tests (3 rules × 3 scenarios: applies, skips, aggregates).

2. **Impact Analyzer Component** → Create `scia/core/impact.py`:
   ```python
   async def analyze_downstream(
       changed_table: str,
       warehouse_adapter: WarehouseAdapter,
       max_depth: int = 3
   ) -> List[DependencyObject]:
       """Recursively find views/tables depending on changed_table.
       Queries: information_schema.views, information_schema.view_dependencies.
       Returns direct + transitive up to max_depth."""
   
   async def analyze_upstream(
       changed_table: str,
       warehouse_adapter: WarehouseAdapter
   ) -> List[DependencyObject]:
       """Find tables/views this table depends on.
       Queries: information_schema.table_constraints (foreign keys).
       Returns upstream dependencies."""
   ```
   Create `tests/core/test_impact.py` with 8 mocked tests: direct dependents, transitive (2, 3, 5 hops), max_depth limit enforced, circular dependency handling, no dependents (empty list), upstream FK detection.

3. **Extend Analyzer Pipeline** → Update `scia/core/analyze.py`:
   ```python
   async def analyze(
       before_schema: List[TableSchema],
       after_schema: List[TableSchema],
       sql_definitions: Optional[Dict[str, str]] = None,
       warehouse_adapter: Optional[WarehouseAdapter] = None,
       max_dependency_depth: int = 3
   ) -> RiskAssessment:
       """Full pipeline: diff → rules → impact → risk.
       If warehouse_adapter provided, enrich findings with dependency analysis."""
   ```
   Add enrichment logic after `apply_rules()`: for each finding, call `analyze_downstream()` and `analyze_upstream()`, wrap in `EnrichedFinding`.

4. **CLI v0.2 Update** → Update `scia/cli/main.py`:
   - Keep existing `analyze` command, add optional flags:
     - `--warehouse {snowflake|databricks|postgres|redshift}` (optional, JSON mode doesn't need it)
     - `--conn-file <path>` (optional connection config)
     - `--dependency-depth <int>` (default: 3, min: 1, max: 10)
     - `--include-upstream` (default: True, can use --no-upstream to disable)
     - `--include-downstream` (default: True, can use --no-downstream to disable)
   - Update input resolver logic: detect JSON vs. SQL vs. DATABASE based on before/after args.
   - Route to appropriate loader (JSON loader, SQL parser, warehouse adapter).
   - Pass `warehouse_adapter` to `analyze()` if provided.
   - Extended tests: `tests/integration/test_cli_sql_mode.py` (4 tests: SQL before + JSON after, JSON before + SQL after, both SQL, graceful parser failure), `tests/integration/test_cli_db_mode.py` (4 tests: schema-to-schema compare, dependency depth honored, upstream/downstream toggled, missing warehouse error).

5. **Output Renderers (Enhanced)** → Update `scia/output/json.py` and `scia/output/markdown.py`:
   - JSON: Add optional `impact_detail` field to each finding (null if no dependencies analyzed).
   - Markdown: Add section "Downstream Impact" with table of affected objects, blast radius.
   - Tests: `tests/output/test_json_with_impact.py` (2 tests: with impact, without impact), `tests/output/test_markdown_with_impact.py` (2 tests).

### Validation Checklist

- [ ] New rules tested and integrated
- [ ] Impact analyzer returns correct direct + transitive dependents
- [ ] max_depth limit enforced (never exceeds param)
- [ ] CLI accepts `--warehouse`, `--conn-file`, `--dependency-depth`
- [ ] v0.1 JSON mode still works unchanged
- [ ] All Phase 0 + Phase 1 tests still pass
- [ ] New feature tests >90% coverage

---

## Phase 3: Test Hardening & Edge Cases — **Weeks 12–13**

### Objective
Comprehensive test suite, edge case handling, graceful degradation validation.

### Steps

1. **Full Backward Compatibility Tests** → Create `tests/integration/test_backward_compat.py` with 5 tests:
   - v0.1 JSON mode produces identical output to v0.1 (regression)
   - v0.1 exit codes unchanged
   - v0.1 --fail-on behavior unchanged
   - v0.2 flags ignored in JSON mode (backward compat)
   - Help text mentions v0.2 options but doesn't break v0.1

2. **Graceful Degradation Tests** → Create `tests/integration/test_graceful_degradation.py` with 6 tests:
   - Warehouse connection fails → skip impact, return schema-based findings only (warn)
   - SQL parsing fails → skip SQL-based rules, return schema-based rules only
   - Views metadata unavailable → no downstream analysis, continue with findings
   - Foreign keys unavailable → no upstream analysis, continue with findings
   - max_depth=1 (minimum) works
   - max_depth=10 (maximum) works

3. **Edge Case Stress Tests** → Create `tests/integration/test_edge_cases.py` with 8 tests:
   - Circular view dependencies (A → B → A) handled without infinite loop
   - Very deep dependency chain (10+ hops), limited by max_depth
   - Large schema (100+ tables, 500+ columns), performance acceptable
   - Special characters in table/column names (quoted identifiers, emojis—if supported)
   - Empty schema (no tables) → no findings
   - No changes detected → risk_score 0, classification LOW
   - Multiple high-risk findings → risk_score aggregates correctly
   - Mixed v0.1 + v0.2 input (JSON before, SQL after) → works correctly

4. **CLI Error Handling Tests** → Create `tests/integration/test_cli_errors.py` with 5 tests:
   - Missing `--warehouse` when DB mode detected → clear error message
   - Invalid `--warehouse` value → graceful error
   - Connection timeout (mocked) → graceful error with retry message
   - Malformed config file → clear error
   - Missing connection credentials → helpful error (check config file)

5. **SQL Parser Edge Cases** → Extend `tests/test_ddl_parser.py` with 5 additional tests:
   - Comments in DDL (ignored)
   - Case insensitivity (CREATE table, create TABLE)
   - Snowflake-specific syntax (IDENTITY, AUTOINCREMENT)
   - Multiple DDL statements with mixed content (some valid, some ignored)
   - Very long column names, table names

### Validation Checklist

- [ ] `pytest tests/integration/test_backward_compat.py` all pass
- [ ] Graceful degradation verified: connection fails → findings returned, no crash
- [ ] Edge cases pass (circular deps, deep graphs, large schemas)
- [ ] Error messages clear and actionable
- [ ] Overall coverage >90%

---

## Phase 4: CLI Refinement & Release Prep — **Weeks 14 (overlap with Phase 3)**

### Objective
Polish CLI, finalize documentation, prepare v0.2.0 release.

### Steps

1. **Help Text & Usage** → Update `scia --help` and `scia analyze --help` with v0.2 flags documented:
   ```
   usage: scia analyze --before <path|SCHEMA.TABLE> --after <path|SCHEMA.TABLE|migration.sql>
     [--warehouse snowflake|databricks|postgres|redshift]
     [--conn-file ~/.scia/warehouse.yaml]
     [--dependency-depth 1-10]
     [--include-upstream] [--include-downstream]
     [--format json|markdown]
     [--fail-on HIGH|MEDIUM|LOW]
   ```

2. **Error Messages** → Add context-specific help:
   - "DB mode requires `--warehouse` flag. Example: `scia analyze --before PROD.ANALYTICS --after DEV.ANALYTICS --warehouse snowflake`"
   - "Connection failed to Snowflake. Check `~/.scia/snowflake.yaml` or provide `--conn-file`."
   - "max_depth must be 1-10, got {value}."

3. **Documentation Update** → Extend `README.md`:
   - Add v0.2 usage examples (SQL, DB modes)
   - Add examples with `--dependency-depth`, `--include-upstream/downstream`
   - Add troubleshooting section (connection issues, SQL parsing)
   - Link to `docs/requirements/requirements_v02.md`

4. **Example Outputs** → Add to `docs/examples/` (create if needed):
   - `v0.1_json_output.json` (backward compat example)
   - `v0.2_json_with_impact.json` (new feature example)
   - `v0.2_markdown_with_impact.md` (new feature example)

5. **Version & Changelog** → Update `pyproject.toml` to v0.2.0. Create `CHANGELOG.md`:
   ```
   ## v0.2.0 (January 28, 2026)
   
   ### New Features
   - SQL migration file parsing (CREATE/ALTER DDL)
   - Live database schema comparison
   - Warehouse abstraction (Snowflake working; Databricks, PostgreSQL, Redshift designed as stubs)
   - Downstream/upstream dependency analysis
   - Extended risk rules (JOIN breakage, GROUP BY breakage)
   - Configurable dependency depth (`--dependency-depth`)
   
   ### Breaking Changes
   - None. v0.1 CLI fully backward compatible.
   
   ### Added
   - `scia/warehouse/base.py` — Warehouse adapter abstraction
   - `scia/warehouse/snowflake.py` — Snowflake implementation
   - `scia/sql/ddl_parser.py` — DDL parsing
   - `scia/core/impact.py` — Dependency analysis
   - New rules: JOIN_KEY_CHANGED, GRAIN_CHANGE, POTENTIAL_BREAKAGE
   
   ### Tests
   - 60+ new tests covering all v0.2 features
   - Backward compatibility verified
   - Graceful degradation tested
   ```

6. **Release Gate** → Checklist before tagging v0.2.0:
   - [ ] All tests pass (`pytest` with no failures)
   - [ ] Coverage >90%
   - [ ] v0.1 regression tests pass
   - [ ] README updated with examples
   - [ ] No TODO/FIXME comments in code
   - [ ] pyproject.toml version bumped
   - [ ] Git tag `v0.2.0` ready

---

## Summary: Test Coverage by Phase

| Phase | Component | Test File | Count | Strategy |
|-------|-----------|-----------|-------|----------|
| **0** | Diff detection | `test_diff.py` | 8 | Unit (fixtures) |
| **0** | Rules (3 v0.1) | `test_rules.py` | 9 | Unit (fixtures) |
| **0** | Risk scoring | `test_risk.py` | 4 | Unit (boundaries) |
| **0** | Analyzer pipeline | `test_analyze.py` | 5 | Integration (mocked) |
| **0** | CLI integration | `integration/test_cli.py` | 8 | Integration (file I/O) |
| **0** | Snowflake adapter | `warehouse/test_snowflake_adapter.py` | 6 | Mocked (no live DB) |
| **1** | Warehouse abstraction | `warehouse/test_adapter_registry.py` | 4 | Unit (interfaces) |
| **1** | DDL parser | `test_ddl_parser.py` | 8 | Unit (SQL parsing) |
| **1** | Input resolver | `test_input_resolver.py` | 6 | Unit (type detection) |
| **1** | Config manager | `config/test_connection.py` | 4 | Unit (file loading) |
| **1** | Extended models | `models/test_extended_models.py` | 3 | Unit (validation) |
| **2** | SQL-based rules (3) | `test_rules.py` + 9 new | 9 | Unit (with sql_signals) |
| **2** | Impact analyzer | `core/test_impact.py` | 8 | Mocked (warehouse calls) |
| **2** | CLI v0.2 SQL mode | `integration/test_cli_sql_mode.py` | 4 | Integration (mocked parser) |
| **2** | CLI v0.2 DB mode | `integration/test_cli_db_mode.py` | 4 | Integration (mocked adapter) |
| **2** | Output (enhanced) | `output/test_json_with_impact.py` | 2 | Unit (model serialization) |
| **2** | Output (Markdown) | `output/test_markdown_with_impact.py` | 2 | Unit (formatting) |
| **3** | Backward compat | `integration/test_backward_compat.py` | 5 | Regression |
| **3** | Graceful degradation | `integration/test_graceful_degradation.py` | 6 | Integration (mocked failures) |
| **3** | Edge cases | `integration/test_edge_cases.py` | 8 | Stress tests |
| **3** | CLI errors | `integration/test_cli_errors.py` | 5 | Error paths |
| **3** | DDL parser extras | `test_ddl_parser.py` + 5 new | 5 | Unit (edge SQL) |
| **TOTAL** | | | **~135 tests** | **>90% coverage** |

---

## Implementation Roadmap (At-a-Glance)

```
Week 1–3:   Phase 0 ✅ v0.1 → production-ready (8 test files, >90% coverage)
Week 4–7:   Phase 1 ✅ Design v0.2 (8 new modules, warehouse abstraction, stubs)
Week 8–11:  Phase 2 ✅ Build v0.2 (SQL rules, impact analysis, extended CLI)
Week 12–13: Phase 3 ✅ Test hardening (edge cases, graceful degradation, compat)
Week 14:    Phase 4 ✅ Release prep (docs, CHANGELOG, v0.2.0 tag)
```

**Total: 14 weeks (10–14 weeks depending on blockers)**

---

## Execution Gates (Must Pass Before Moving On)

| Gate | Criteria | Phase |
|------|----------|-------|
| **v0.1 Gate** | All Phase 0 tests pass, >90% coverage, README updated | Before Phase 1 |
| **Architecture Gate** | Warehouse abstraction working, all adapters stubbed/tested | Before Phase 2 |
| **Feature Gate** | v0.2 rules integrated, impact analyzer returns correct results | Before Phase 3 |
| **Quality Gate** | Backward compat tests pass, graceful degradation verified | Before Phase 4 |
| **Release Gate** | All tests pass, no TODOs, CHANGELOG complete, docs ready | Before v0.2.0 tag |

---

## Key Decisions Locked In

✅ **Phase 0 first** — Do not start Phase 1 until v0.1 is production-ready.  
✅ **Snowflake only (working)** — Databricks, Postgres, Redshift are stubs with NotImplementedError.  
✅ **DDL scope strict** — CREATE TABLE, ALTER ADD/DROP/MODIFY/RENAME. Future extensions welcome.  
✅ **Dependency depth: max_depth=3 (default)** — Configurable 1–10 via CLI flag.  
✅ **Backward compatible** — v0.1 JSON mode unchanged; all new features additive.  
✅ **Test strategy first** — Design tests before code; >90% coverage required.  
✅ **Graceful degradation** — Missing signals (no metadata, connection fails) → omit related findings, not errors.

---

## Refinement Notes

Use this space to track refinements, decisions, or open questions:

- [ ] **Phase 0 blockers**: Any existing test gaps to prioritize?
- [ ] **Warehouse adapter**: Any Snowflake-specific considerations (auth, query performance)?
- [ ] **DDL parser**: Use sqlglot or custom regex parser?
- [ ] **Impact analyzer**: Async or sync implementation?
- [ ] **Performance targets**: Any specific SLA for dependency analysis on large schemas?

---

**Status: Ready for execution** 🚀
