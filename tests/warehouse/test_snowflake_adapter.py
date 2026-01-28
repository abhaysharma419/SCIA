"""Tests for Snowflake warehouse adapter."""
from unittest.mock import MagicMock, patch

import pytest

from scia.warehouse.snowflake import SnowflakeAdapter


@pytest.fixture
def adapter():
    """Create a Snowflake adapter instance."""
    return SnowflakeAdapter()


def test_snowflake_adapter_init(adapter):
    """Test adapter initialization."""
    assert adapter.conn is None


def test_snowflake_adapter_connect_success(adapter):
    """Test successful Snowflake connection."""
    mock_conn = MagicMock()

    with patch('snowflake.connector.connect', return_value=mock_conn):
        config = {
            'account': 'test-account',
            'user': 'test-user',
            'password': 'test-password'
        }
        adapter.connect(config)
        assert adapter.conn is not None


def test_snowflake_adapter_connect_failure(adapter):
    """Test connection failure handling."""
    import snowflake.connector  # pylint: disable=import-error,no-name-in-module

    with patch('snowflake.connector.connect',
               side_effect=snowflake.connector.errors.Error("Connection failed")):
        config = {'account': 'invalid'}
        with pytest.raises(snowflake.connector.errors.Error):
            adapter.connect(config)


def test_snowflake_adapter_fetch_schema_success(adapter):
    """Test successful schema fetch."""
    # Mock connection and cursor
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ('PUBLIC', 'USERS', 'USER_ID', 'INTEGER', 'NO', 1),
        ('PUBLIC', 'USERS', 'NAME', 'VARCHAR', 'YES', 2),
        ('PUBLIC', 'ORDERS', 'ORDER_ID', 'INTEGER', 'NO', 1),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    adapter.conn = mock_conn

    schemas = adapter.fetch_schema('PROD', 'PUBLIC')

    assert len(schemas) == 2
    assert schemas[0].table_name == 'USERS'
    assert len(schemas[0].columns) == 2
    assert schemas[0].columns[0].column_name == 'USER_ID'


def test_snowflake_adapter_fetch_schema_no_connection(adapter):
    """Test schema fetch without connection."""
    schemas = adapter.fetch_schema('PROD', 'PUBLIC')
    assert schemas == []


def test_snowflake_adapter_fetch_schema_failure(adapter):
    """Test schema fetch failure handling."""
    import snowflake.connector  # pylint: disable=import-error,no-name-in-module

    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = snowflake.connector.errors.Error("Query failed")

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    adapter.conn = mock_conn

    schemas = adapter.fetch_schema('PROD', 'PUBLIC')
    assert schemas == []


def test_snowflake_adapter_fetch_views_success(adapter):
    """Test successful views fetch."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ('VIEW_A', 'SELECT * FROM USERS'),
        ('VIEW_B', 'SELECT * FROM ORDERS'),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    adapter.conn = mock_conn

    views = adapter.fetch_views('PROD', 'PUBLIC')

    assert len(views) == 2
    assert views['VIEW_A'] == 'SELECT * FROM USERS'
    assert views['VIEW_B'] == 'SELECT * FROM ORDERS'


def test_snowflake_adapter_fetch_views_no_connection(adapter):
    """Test views fetch without connection."""
    views = adapter.fetch_views('PROD', 'PUBLIC')
    assert views == {}


def test_snowflake_adapter_fetch_foreign_keys_success(adapter):
    """Test successful foreign keys fetch."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ('FK_USER_ID', 'ORDERS', 'USER_ID', 'USERS', 'USER_ID'),
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    adapter.conn = mock_conn

    fks = adapter.fetch_foreign_keys('PROD', 'PUBLIC')

    assert len(fks) == 1
    assert fks[0]['constraint_name'] == 'FK_USER_ID'
    assert fks[0]['table_name'] == 'ORDERS'


def test_snowflake_adapter_fetch_foreign_keys_no_connection(adapter):
    """Test foreign keys fetch without connection."""
    fks = adapter.fetch_foreign_keys('PROD', 'PUBLIC')
    assert fks == []


def test_snowflake_adapter_parse_table_references(adapter):
    """Test table reference extraction from SQL."""
    with patch('scia.sql.parser.extract_table_references',
               return_value=['SCHEMA.USERS', 'SCHEMA.ORDERS']):
        refs = adapter.parse_table_references('SELECT * FROM USERS JOIN ORDERS')
        assert refs == ['SCHEMA.USERS', 'SCHEMA.ORDERS']


def test_snowflake_adapter_parse_table_references_failure(adapter):
    """Test table reference extraction failure."""
    with patch('scia.sql.parser.extract_table_references',
               side_effect=Exception("Parse error")):
        refs = adapter.parse_table_references('INVALID SQL')
        assert refs == []


def test_snowflake_adapter_close(adapter):
    """Test connection close."""
    mock_conn = MagicMock()
    adapter.conn = mock_conn

    adapter.close()

    assert adapter.conn is None
    mock_conn.close.assert_called_once()


def test_snowflake_adapter_close_no_connection(adapter):
    """Test close with no connection."""
    adapter.conn = None
    adapter.close()  # Should not raise
    assert adapter.conn is None
