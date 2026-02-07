"""Common test fixtures."""
# pylint: disable=redefined-outer-name,too-many-arguments,too-many-positional-arguments
from pathlib import Path
import pytest
from scia.models.schema import ColumnSchema, TableSchema
from scia.models.finding import Finding, FindingType, Severity
from scia.core.diff import SchemaDiff

@pytest.fixture
def fixtures_dir():
    """Fixture for the directory containing test data files."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def column_factory():
    """Factory to create ColumnSchema instances for testing."""
    def _make_column(
        schema_name="PUBLIC",
        table_name="TEST_TABLE",
        column_name="TEST_COL",
        data_type="VARCHAR",
        is_nullable=True,
        ordinal_position=1
    ):
        return ColumnSchema(
            schema_name=schema_name,
            table_name=table_name,
            column_name=column_name,
            data_type=data_type,
            is_nullable=is_nullable,
            ordinal_position=ordinal_position
        )
    return _make_column

@pytest.fixture
def table_factory(column_factory):
    """Factory to create TableSchema instances for testing."""
    def _make_table(
        schema_name="PUBLIC",
        table_name="TEST_TABLE",
        columns=None
    ):
        if columns is None:
            columns = [column_factory(table_name=table_name)]
        return TableSchema(
            schema_name=schema_name,
            table_name=table_name,
            columns=columns
        )
    return _make_table

@pytest.fixture
def finding_factory():
    """Factory to create Finding instances for testing."""
    def _make_finding(
        finding_type=FindingType.COLUMN_REMOVED,
        severity=Severity.HIGH,
        base_risk=70,
        evidence=None,
        description="Test finding"
    ):
        if evidence is None:
            evidence = {"table": "T", "column": "C"}
        return Finding(
            finding_type=finding_type,
            severity=severity,
            base_risk=base_risk,
            evidence=evidence,
            description=description
        )
    return _make_finding

@pytest.fixture
def schema_diff_factory():
    """Factory to create SchemaDiff instances for testing."""
    def _make_diff(changes=None):
        if changes is None:
            changes = []
        return SchemaDiff(changes=changes)
    return _make_diff
