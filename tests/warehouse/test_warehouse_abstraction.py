"""Tests for warehouse abstraction layer."""
import pytest

from scia.warehouse.base import WarehouseAdapter


def test_warehouse_adapter_is_abstract():
    """Test that WarehouseAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        WarehouseAdapter()


def test_warehouse_adapter_requires_connect():
    """Test that connect method must be implemented."""
    class IncompleteAdapter(WarehouseAdapter):
        pass

    with pytest.raises(TypeError):
        IncompleteAdapter()


def test_warehouse_adapter_requires_fetch_schema():
    """Test that fetch_schema method must be implemented."""
    class PartialAdapter(WarehouseAdapter):
        def connect(self, config):
            pass
        def fetch_views(self, database, schema):
            return {}
        def fetch_foreign_keys(self, database, schema):
            return []
        def parse_table_references(self, sql):
            return []
        def close(self):
            pass

    with pytest.raises(TypeError):
        PartialAdapter()


def test_warehouse_adapter_requires_all_methods():
    """Test that all abstract methods must be implemented."""
    abstract_methods = {
        'connect',
        'fetch_schema',
        'fetch_views',
        'fetch_foreign_keys',
        'parse_table_references',
        'close'
    }
    
    # Verify all methods are abstract
    for method_name in abstract_methods:
        assert hasattr(WarehouseAdapter, method_name)
        method = getattr(WarehouseAdapter, method_name)
        # Check if method is marked as abstract
        assert hasattr(method, '__isabstractmethod__')
        assert method.__isabstractmethod__ is True
