"""Tests for impact analysis component."""
# pylint: disable=redefined-outer-name
from unittest.mock import MagicMock

import pytest

from scia.core.impact import analyze_downstream, analyze_upstream


@pytest.fixture
def mock_adapter():
    adapter = MagicMock(spec=WarehouseAdapter)
    adapter.fetch_views.return_value = {
        "view1": "SELECT * FROM public.table1",
        "view2": "SELECT * FROM public.view1"
    }
    adapter.parse_table_references.side_effect = lambda sql: [
        "public.table1" if "table1" in sql else "public.view1"
    ]
    adapter.fetch_foreign_keys.return_value = [
        {
            "table_name": "table1",
            "referenced_table": "parent_table",
            "constraint_name": "fk_1"
        }
    ]
    return adapter

@pytest.mark.asyncio
async def test_analyze_downstream_direct(mock_adapter):
    # table1 -> view1
    dependents = await analyze_downstream("public.table1", mock_adapter, max_depth=1)
    
    assert len(dependents) == 1
    assert dependents[0].name == "view1"
    assert dependents[0].object_type == "VIEW"

@pytest.mark.asyncio
async def test_analyze_downstream_transitive(mock_adapter):
    # table1 -> view1 -> view2
    dependents = await analyze_downstream("public.table1", mock_adapter, max_depth=2)
    
    assert len(dependents) == 2
    names = [d.name for d in dependents]
    assert "view1" in names
    assert "view2" in names

@pytest.mark.asyncio
async def test_analyze_upstream(mock_adapter):
    # table1 -> parent_table
    upstream = await analyze_upstream("public.table1", mock_adapter)
    
    assert len(upstream) == 1
    assert upstream[0].name == "parent_table"
    assert upstream[0].object_type == "TABLE"
    assert upstream[0].is_critical is True

@pytest.mark.asyncio
async def test_analyze_downstream_max_depth(mock_adapter):
    # depth 1 should only return view1
    dependents = await analyze_downstream("public.table1", mock_adapter, max_depth=1)
    assert len(dependents) == 1
    assert dependents[0].name == "view1"

@pytest.mark.asyncio
async def test_analyze_downstream_no_views(mock_adapter):
    mock_adapter.fetch_views.return_value = {}
    dependents = await analyze_downstream("public.table1", mock_adapter)
    assert len(dependents) == 0
