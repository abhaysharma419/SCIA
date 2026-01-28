"""Tests for DDL parser."""
import pytest

from scia.models.schema import ColumnSchema, TableSchema
from scia.sql.ddl_parser import (
    extract_table_references,
    parse_ddl_to_schema,
)


def test_parse_create_table_simple():
    """Test parsing a simple CREATE TABLE statement."""
    ddl = """
    CREATE TABLE users (
        user_id INTEGER NOT NULL,
        name VARCHAR(100)
    )
    """
    schemas = parse_ddl_to_schema(ddl)

    assert len(schemas) == 1
    assert schemas[0].table_name == 'USERS'
    assert len(schemas[0].columns) == 2
    assert schemas[0].columns[0].column_name == 'USER_ID'
    assert schemas[0].columns[0].is_nullable is False
    assert schemas[0].columns[1].column_name == 'NAME'
    assert schemas[0].columns[1].is_nullable is True


def test_parse_create_table_multiple_columns():
    """Test parsing CREATE TABLE with multiple columns."""
    ddl = """
    CREATE TABLE orders (
        order_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        total DECIMAL(10,2),
        created_at TIMESTAMP
    )
    """
    schemas = parse_ddl_to_schema(ddl)

    assert len(schemas) == 1
    assert len(schemas[0].columns) == 4
    assert all(col.table_name == 'ORDERS' for col in schemas[0].columns)


def test_parse_create_table_with_constraints():
    """Test parsing CREATE TABLE with various constraints."""
    ddl = """
    CREATE TABLE products (
        product_id INTEGER NOT NULL,
        name VARCHAR NOT NULL,
        price DECIMAL NOT NULL
    )
    """
    schemas = parse_ddl_to_schema(ddl)

    assert len(schemas) == 1
    assert schemas[0].columns[0].is_nullable is False
    assert schemas[0].columns[1].is_nullable is False


def test_parse_multiple_create_tables():
    """Test parsing multiple CREATE TABLE statements."""
    ddl = """
    CREATE TABLE users (
        user_id INTEGER
    );

    CREATE TABLE orders (
        order_id INTEGER
    );
    """
    schemas = parse_ddl_to_schema(ddl)

    assert len(schemas) == 2
    table_names = {s.table_name for s in schemas}
    assert 'USERS' in table_names
    assert 'ORDERS' in table_names


def test_parse_empty_ddl():
    """Test parsing empty DDL string."""
    schemas = parse_ddl_to_schema("")
    assert schemas == []


def test_parse_invalid_ddl():
    """Test parsing invalid DDL gracefully."""
    ddl = "THIS IS NOT VALID SQL AT ALL!!!"
    schemas = parse_ddl_to_schema(ddl)
    # Should return empty list without raising
    assert isinstance(schemas, list)


def test_parse_unsupported_statements():
    """Test that unsupported statements are gracefully skipped."""
    ddl = """
    CREATE TABLE users (user_id INTEGER);
    CREATE PROCEDURE proc_name() BEGIN END;
    CREATE TABLE orders (order_id INTEGER);
    """
    schemas = parse_ddl_to_schema(ddl)

    # Should get both tables, skipping the procedure
    assert len(schemas) == 2


def test_parse_snowflake_syntax():
    """Test Snowflake-specific DDL syntax."""
    ddl = """
    CREATE TABLE analytics_table (
        id INTEGER IDENTITY,
        created_date DATE,
        value VARIANT
    )
    """
    schemas = parse_ddl_to_schema(ddl)

    assert len(schemas) == 1
    assert len(schemas[0].columns) == 3


def test_ordinal_position():
    """Test that ordinal positions are correctly set."""
    ddl = """
    CREATE TABLE test (
        col1 INTEGER,
        col2 VARCHAR,
        col3 BOOLEAN
    )
    """
    schemas = parse_ddl_to_schema(ddl)

    assert schemas[0].columns[0].ordinal_position == 1
    assert schemas[0].columns[1].ordinal_position == 2
    assert schemas[0].columns[2].ordinal_position == 3


def test_extract_table_references_single_table():
    """Test extracting table references from SELECT with single table."""
    sql = "SELECT * FROM users"
    tables = extract_table_references(sql)

    assert 'USERS' in tables


def test_extract_table_references_multiple_tables():
    """Test extracting table references from JOIN query."""
    sql = """
    SELECT u.user_id, o.order_id
    FROM users u
    JOIN orders o ON u.user_id = o.user_id
    """
    tables = extract_table_references(sql)

    assert 'USERS' in tables
    assert 'ORDERS' in tables


def test_extract_table_references_qualified_names():
    """Test extracting qualified table names."""
    sql = "SELECT * FROM schema.users"
    tables = extract_table_references(sql)

    assert 'SCHEMA.USERS' in tables


def test_extract_table_references_no_tables():
    """Test extracting references from query with no tables."""
    sql = "SELECT 1 + 1"
    tables = extract_table_references(sql)

    assert tables == []


def test_extract_table_references_invalid_sql():
    """Test graceful handling of invalid SQL."""
    sql = "NOT VALID SQL HERE"
    tables = extract_table_references(sql)

    # Should return empty list without raising
    assert isinstance(tables, list)
