"""Tests for ALTER TABLE parsing logic."""
import pytest
from scia.models.schema import TableSchema, ColumnSchema
from scia.sql.ddl_parser import parse_ddl_to_schema

def test_alter_table_add_column():
    """Test ALTER TABLE ADD COLUMN."""
    base_schema = [
        TableSchema(
            schema_name="PUBLIC",
            table_name="USERS",
            columns=[
                ColumnSchema(schema_name="PUBLIC", table_name="USERS", column_name="ID", data_type="INT", is_nullable=False, ordinal_position=1)
            ]
        )
    ]
    
    ddl = "ALTER TABLE users ADD COLUMN email VARCHAR(255)"
    updated_schemas = parse_ddl_to_schema(ddl, base_schemas=base_schema)
    
    assert len(updated_schemas) == 1
    assert len(updated_schemas[0].columns) == 2
    assert updated_schemas[0].columns[1].column_name == "EMAIL"
    assert updated_schemas[0].columns[1].data_type == "VARCHAR(255)"

def test_alter_table_drop_column():
    """Test ALTER TABLE DROP COLUMN."""
    base_schema = [
        TableSchema(
            schema_name="PUBLIC",
            table_name="USERS",
            columns=[
                ColumnSchema(schema_name="PUBLIC", table_name="USERS", column_name="ID", data_type="INT", is_nullable=False, ordinal_position=1),
                ColumnSchema(schema_name="PUBLIC", table_name="USERS", column_name="EMAIL", data_type="VARCHAR", is_nullable=True, ordinal_position=2)
            ]
        )
    ]
    
    ddl = "ALTER TABLE users DROP COLUMN email"
    updated_schemas = parse_ddl_to_schema(ddl, base_schemas=base_schema)
    
    assert len(updated_schemas) == 1
    assert len(updated_schemas[0].columns) == 1
    assert updated_schemas[0].columns[0].column_name == "ID"

def test_alter_table_rename_column():
    """Test ALTER TABLE RENAME COLUMN."""
    base_schema = [
        TableSchema(
            schema_name="PUBLIC",
            table_name="USERS",
            columns=[
                ColumnSchema(schema_name="PUBLIC", table_name="USERS", column_name="ID", data_type="INT", is_nullable=False, ordinal_position=1)
            ]
        )
    ]
    
    ddl = "ALTER TABLE users RENAME COLUMN id TO user_id"
    updated_schemas = parse_ddl_to_schema(ddl, base_schemas=base_schema)
    
    assert len(updated_schemas) == 1
    assert updated_schemas[0].columns[0].column_name == "USER_ID"

def test_alter_table_modify_column():
    """Test ALTER TABLE MODIFY COLUMN."""
    base_schema = [
        TableSchema(
            schema_name="PUBLIC",
            table_name="USERS",
            columns=[
                ColumnSchema(schema_name="PUBLIC", table_name="USERS", column_name="ID", data_type="INT", is_nullable=True, ordinal_position=1)
            ]
        )
    ]
    
    # Snowflake uses ALTER COLUMN or MODIFY
    # sqlglot parses ALTER TABLE ... ALTER COLUMN ... TYPE ... better for Snowflake
    ddl = "ALTER TABLE users ALTER COLUMN id TYPE BIGINT"
    updated_schemas = parse_ddl_to_schema(ddl, base_schemas=base_schema)
    
    assert len(updated_schemas) == 1
    assert updated_schemas[0].columns[0].data_type == "BIGINT"

def test_alter_table_modify_column_snowflake_syntax():
    """Test ALTER TABLE MODIFY COLUMN with Snowflake syntax."""
    base_schema = [
        TableSchema(
            schema_name="PUBLIC",
            table_name="USERS",
            columns=[
                ColumnSchema(schema_name="PUBLIC", table_name="USERS", column_name="USERNAME", data_type="VARCHAR(100)", is_nullable=True, ordinal_position=1)
            ]
        )
    ]
    
    # Snowflake MODIFY COLUMN syntax (parsed as Command by sqlglot)
    ddl = "ALTER TABLE SCIA_TEST_DB.PUBLIC.USERS modify column USERNAME VARCHAR(255)"
    updated_schemas = parse_ddl_to_schema(ddl, base_schemas=base_schema)
    
    assert len(updated_schemas) == 1
    assert updated_schemas[0].columns[0].data_type == "VARCHAR(255)"

def test_alter_table_with_dialect_parameter():
    """Test that dialect parameter is passed correctly to parser."""
    base_schema = [
        TableSchema(
            schema_name="PUBLIC",
            table_name="USERS",
            columns=[
                ColumnSchema(schema_name="PUBLIC", table_name="USERS", column_name="USERNAME", data_type="VARCHAR(100)", is_nullable=True, ordinal_position=1)
            ]
        )
    ]
    
    # Snowflake dialect should convert MODIFY COLUMN
    ddl = "ALTER TABLE users MODIFY COLUMN username VARCHAR(255)"
    updated_schemas = parse_ddl_to_schema(ddl, base_schemas=base_schema, dialect='snowflake')
    assert updated_schemas[0].columns[0].data_type == "VARCHAR(255)"
    
    # Reset schema
    base_schema = [
        TableSchema(
            schema_name="PUBLIC",
            table_name="USERS",
            columns=[
                ColumnSchema(schema_name="PUBLIC", table_name="USERS", column_name="USERNAME", data_type="VARCHAR(100)", is_nullable=True, ordinal_position=1)
            ]
        )
    ]
    
    # Other dialects should not convert (no preprocessor registered)
    updated_schemas = parse_ddl_to_schema(ddl, base_schemas=base_schema, dialect='postgres')
    assert updated_schemas[0].columns[0].data_type == "VARCHAR(100)"

def test_multiple_alter_statements():
    """Test multiple ALTER statements in one script."""
    base_schema = [
        TableSchema(
            schema_name="PUBLIC",
            table_name="USERS",
            columns=[
                ColumnSchema(schema_name="PUBLIC", table_name="USERS", column_name="ID", data_type="INT", is_nullable=False, ordinal_position=1)
            ]
        )
    ]
    
    ddl = """
    ALTER TABLE users ADD COLUMN first_name VARCHAR;
    ALTER TABLE users ADD COLUMN last_name VARCHAR;
    ALTER TABLE users DROP COLUMN id;
    """
    updated_schemas = parse_ddl_to_schema(ddl, base_schemas=base_schema)
    
    assert len(updated_schemas) == 1
    col_names = [c.column_name for c in updated_schemas[0].columns]
    assert "FIRST_NAME" in col_names
    assert "LAST_NAME" in col_names
    assert "ID" not in col_names
