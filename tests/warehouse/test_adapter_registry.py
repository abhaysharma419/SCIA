"""Tests for warehouse adapter registry."""
import pytest

from scia.warehouse import (
    UnsupportedWarehouseError,
    WarehouseNotImplementedError,
    get_adapter,
    list_planned_warehouses,
    list_supported_warehouses,
)
from scia.warehouse.snowflake import SnowflakeAdapter


def test_get_snowflake_adapter():
    """Test getting Snowflake adapter."""
    adapter = get_adapter('snowflake')
    assert isinstance(adapter, SnowflakeAdapter)


def test_get_snowflake_adapter_case_insensitive():
    """Test that adapter retrieval is case-insensitive."""
    adapter1 = get_adapter('SNOWFLAKE')
    adapter2 = get_adapter('SnowFlake')
    assert isinstance(adapter1, SnowflakeAdapter)
    assert isinstance(adapter2, SnowflakeAdapter)


def test_get_unsupported_warehouse():
    """Test requesting an unsupported warehouse type."""
    with pytest.raises(UnsupportedWarehouseError, match="Unsupported warehouse: 'mysql'"):
        get_adapter('mysql')


def test_get_databricks_not_implemented():
    """Test that Databricks adapter is not yet implemented."""
    with pytest.raises(WarehouseNotImplementedError, 
                      match="not yet implemented"):
        get_adapter('databricks')


def test_get_postgres_not_implemented():
    """Test that PostgreSQL adapter is not yet implemented."""
    with pytest.raises(WarehouseNotImplementedError,
                      match="not yet implemented"):
        get_adapter('postgres')


def test_get_redshift_not_implemented():
    """Test that Redshift adapter is not yet implemented."""
    with pytest.raises(WarehouseNotImplementedError,
                      match="not yet implemented"):
        get_adapter('redshift')


def test_list_supported_warehouses():
    """Test listing supported warehouse types."""
    supported = list_supported_warehouses()
    assert 'snowflake' in supported
    assert 'databricks' not in supported
    assert 'postgres' not in supported
    assert 'redshift' not in supported


def test_list_planned_warehouses():
    """Test listing planned (stub) warehouse types."""
    planned = list_planned_warehouses()
    assert 'snowflake' not in planned
    assert 'databricks' in planned
    assert 'postgres' in planned
    assert 'redshift' in planned
