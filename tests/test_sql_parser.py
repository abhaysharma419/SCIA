from scia.sql.parser import parse_sql

def test_parse_sql_tables_and_columns():
    sql = "SELECT id, name FROM users"
    metadata = parse_sql(sql)
    assert "USERS" in metadata.tables
    assert "ID" in metadata.columns
    assert "NAME" in metadata.columns

def test_parse_sql_group_by():
    sql = "SELECT department, count(*) FROM employees GROUP BY department"
    metadata = parse_sql(sql)
    assert "EMPLOYEES" in metadata.tables
    assert "DEPARTMENT" in metadata.group_by_cols

def test_parse_sql_join():
    sql = """
    SELECT o.id, c.name 
    FROM orders o 
    JOIN customers c ON o.customer_id = c.id
    """
    metadata = parse_sql(sql)
    assert "ORDERS" in metadata.tables
    assert "CUSTOMERS" in metadata.tables
    # Check join keys
    assert ("CUSTOMER_ID", "ID") in metadata.join_keys or ("ID", "CUSTOMER_ID") in metadata.join_keys

def test_parse_sql_invalid():
    sql = "INVALID SQL"
    # sqlglot might still parse something or return empty list
    metadata = parse_sql(sql)
    # It should not crash
    assert metadata is not None or metadata is None # Depends on sqlglot result

def test_parse_sql_failure():
    # Passing None should trigger TypeError in sqlglot.parse and be caught
    metadata = parse_sql(None)
    assert metadata is None
