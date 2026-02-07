"""Tests for DDL parser."""
import pytest

from scia.sql.ddl_parser import (
    extract_table_references,
    parse_ddl_to_schema,
)
from scia.models.schema import TableSchema, ColumnSchema


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
    assert not schemas


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


def test_parse_comments_in_sql():
    """Test that comments in SQL are ignored."""
    ddl = """
    -- This is a comment
    CREATE TABLE users (
        user_id INTEGER /* inline comment */,
        name VARCHAR(100) -- another comment
    );
    """
    schemas = parse_ddl_to_schema(ddl)
    assert len(schemas) == 1
    assert len(schemas[0].columns) == 2


def test_parse_case_insensitivity():
    """Test that keywords are case-insensitive."""
    ddl = "create table Users (User_Id integer, NAME varchar)"
    schemas = parse_ddl_to_schema(ddl)
    assert schemas[0].table_name == 'USERS'
    assert schemas[0].columns[0].column_name == 'USER_ID'
    assert schemas[0].columns[1].column_name == 'NAME'


def test_parse_alter_table_add_column_with_base():
    """Test parsing ALTER TABLE ADD COLUMN using base schemas."""
    base_schema = [
        TableSchema(schema_name="S", table_name="T1", columns=[
            ColumnSchema(schema_name="S", table_name="T1", column_name="ID", data_type="INT", is_nullable=True, ordinal_position=1)
        ])
    ]
    ddl = "ALTER TABLE S.T1 ADD COLUMN NEW_COL VARCHAR"
    schemas = parse_ddl_to_schema(ddl, base_schemas=base_schema)
    
    assert len(schemas) == 1
    assert len(schemas[0].columns) == 2
    assert "NEW_COL" in [c.column_name for c in schemas[0].columns]


def test_parse_alter_table_rename_column():
    """Test parsing ALTER TABLE RENAME COLUMN."""
    base_schema = [
        TableSchema(schema_name="S", table_name="T1", columns=[
            ColumnSchema(schema_name="S", table_name="T1", column_name="OLD_NAME", data_type="INT", is_nullable=True, ordinal_position=1)
        ])
    ]
    ddl = "ALTER TABLE S.T1 RENAME COLUMN OLD_NAME TO NEW_NAME"
    schemas = parse_ddl_to_schema(ddl, base_schemas=base_schema)
    
    assert len(schemas) == 1
    assert schemas[0].columns[0].column_name == "NEW_NAME"


def test_parse_very_long_identifiers():
    """Test that very long identifiers are handled."""
    long_name = "A" * 128
    ddl = f"CREATE TABLE {long_name} ({long_name} INTEGER)"
    schemas = parse_ddl_to_schema(ddl)
    
    assert schemas[0].table_name == long_name.upper()
    assert schemas[0].columns[0].column_name == long_name.upper()
