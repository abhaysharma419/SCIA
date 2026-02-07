"""Tests for test_snowflake_adapter."""
# pylint: disable=redefined-outer-name
from unittest.mock import MagicMock, patch
import pytest
from scia.metadata.snowflake import SnowflakeInspector

@pytest.fixture
def mock_snowflake_connection():
    """Fixture to mock snowflake connection."""
    with patch("snowflake.connector.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        yield mock_conn

def test_snowflake_connection_success(mock_snowflake_connection):
    """Test function."""
    inspector = SnowflakeInspector({"user": "test"})
    inspector.connect()
    assert inspector.conn is not None

def test_snowflake_connection_failure():
    """Test function."""
    with patch("snowflake.connector.connect", side_effect=Exception("Conn failed")):
        inspector = SnowflakeInspector({"user": "test"})
        with pytest.raises(Exception):
            inspector.connect()

def test_snowflake_fetch_schema_success(mock_snowflake_connection):
    """Test function."""
    mock_cursor = MagicMock()
    mock_snowflake_connection.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        ("PUBLIC", "T1", "C1", "INT", "YES", 1),
        ("PUBLIC", "T1", "C2", "TEXT", "NO", 2)
    ]

    inspector = SnowflakeInspector({"user": "test"})
    schema = inspector.fetch_schema("DB", "PUBLIC")

    assert len(schema) == 1
    assert schema[0].table_name == "T1"
    assert len(schema[0].columns) == 2

def test_snowflake_fetch_schema_empty(mock_snowflake_connection):
    """Test function."""
    mock_cursor = MagicMock()
    mock_snowflake_connection.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    inspector = SnowflakeInspector({"user": "test"})
    schema = inspector.fetch_schema("DB", "PUBLIC")
    assert not schema

def test_snowflake_fetch_views_success(mock_snowflake_connection):
    """Test function."""
    mock_cursor = MagicMock()
    mock_snowflake_connection.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        ("V1", "CREATE VIEW V1 AS SELECT 1"),
        ("V2", "CREATE VIEW V2 AS SELECT 2")
    ]

    inspector = SnowflakeInspector({"user": "test"})
    views = inspector.fetch_view_definitions("DB", "PUBLIC")

    assert len(views) == 2
    assert views["V1"] == "CREATE VIEW V1 AS SELECT 1"

def test_snowflake_fetch_foreign_keys_stub(mock_snowflake_connection):  # pylint: disable=unused-argument
    """Test function."""
    inspector = SnowflakeInspector({"user": "test"})
    fks = inspector.fetch_foreign_keys("DB", "PUBLIC")
    assert not fks

