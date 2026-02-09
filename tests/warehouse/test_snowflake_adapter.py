"""Tests for Snowflake warehouse adapter."""
# pylint: disable=redefined-outer-name
from unittest.mock import MagicMock, patch

import pytest
import snowflake.connector

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
        ('PROD', 'PUBLIC', 'USERS', 'USER_ID', 'INTEGER', 'NO', 1),
        ('PROD', 'PUBLIC', 'USERS', 'NAME', 'VARCHAR', 'YES', 2),
        ('PROD', 'PUBLIC', 'ORDERS', 'ORDER_ID', 'INTEGER', 'NO', 1),
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
    # Mock result for SHOW IMPORTED KEYS
    # Indices: [3]=pk_table_name, [4]=pk_column_name, [7]=fk_table_name, [8]=fk_column_name, [12]=fk_name
    row = [None] * 17
    row[3] = 'USERS'
    row[4] = 'USER_ID'
    row[7] = 'ORDERS'
    row[8] = 'USER_ID'
    row[12] = 'FK_USER_ID'

    mock_cursor.fetchall.return_value = [row]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    adapter.conn = mock_conn

    fks = adapter.fetch_foreign_keys('PROD', 'PUBLIC')

    assert len(fks) == 1
    assert fks[0]['constraint_name'] == 'FK_USER_ID'
    assert fks[0]['table_name'] == 'ORDERS'
    assert fks[0]['column_name'] == 'USER_ID'
    assert fks[0]['referenced_table'] == 'USERS'
    assert fks[0]['referenced_column'] == 'USER_ID'


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


def test_snowflake_adapter_resolve_context(adapter):
    """Test resolution of database and schema from Snowflake session."""
    mock_cursor = MagicMock()
    # First call for context resolution
    mock_cursor.fetchone.return_value = ('MOCKED_DB', 'MOCKED_SCHEMA')
    # Second call for the metadata query (e.g., SHOW IMPORTED KEYS)
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    adapter.conn = mock_conn

    # Call with empty strings to trigger resolution
    adapter.fetch_foreign_keys('', '')

    # Verify context was fetched
    mock_cursor.execute.assert_any_call("SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()")
    # Verify the metadata query used the resolved names
    mock_cursor.execute.assert_any_call("SHOW IMPORTED KEYS IN SCHEMA MOCKED_DB.MOCKED_SCHEMA")


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
