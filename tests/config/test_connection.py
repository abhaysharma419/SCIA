"""Tests for connection configuration."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from scia.config.connection import (
    ConnectionConfigError,
    load_connection_config,
    validate_connection_config,
)


def test_load_from_explicit_file(tmp_path):
    """Test loading config from explicit file."""
    config_file = tmp_path / "snowflake.yaml"
    config_data = {
        'account': 'test-account',
        'user': 'test-user',
        'password': 'test-password'
    }
    config_file.write_text(yaml.dump(config_data))

    config = load_connection_config('snowflake', str(config_file))

    assert config['account'] == 'test-account'
    assert config['user'] == 'test-user'


def test_load_from_default_path(tmp_path):
    """Test loading config from default ~/.scia path."""
    with patch('pathlib.Path.home', return_value=tmp_path):
        # Create .scia directory and config file
        scia_dir = tmp_path / '.scia'
        scia_dir.mkdir()
        config_file = scia_dir / 'snowflake.yaml'

        config_data = {
            'account': 'default-account',
            'user': 'default-user',
            'password': 'default-password'
        }
        config_file.write_text(yaml.dump(config_data))

        config = load_connection_config('snowflake')

        assert config['account'] == 'default-account'


def test_load_from_environment_variables(tmp_path):
    """Test loading config from environment variables."""
    with patch.dict(os.environ, {
        'SNOWFLAKE_ACCOUNT': 'env-account',
        'SNOWFLAKE_USER': 'env-user',
        'SNOWFLAKE_PASSWORD': 'env-password'
    }):
        with patch('pathlib.Path.home', return_value=tmp_path):
            config = load_connection_config('snowflake')

            assert config['account'] == 'env-account'
            assert config['user'] == 'env-user'


def test_load_explicit_overrides_default(tmp_path):
    """Test that explicit file overrides default path."""
    explicit_file = tmp_path / "explicit.yaml"
    explicit_data = {'account': 'explicit-account', 'user': 'explicit-user'}
    explicit_file.write_text(yaml.dump(explicit_data))

    default_path = tmp_path / '.scia' / 'snowflake.yaml'
    default_path.parent.mkdir(parents=True)
    default_data = {'account': 'default-account'}
    default_path.write_text(yaml.dump(default_data))

    with patch('pathlib.Path.home', return_value=tmp_path):
        config = load_connection_config('snowflake', str(explicit_file))

        assert config['account'] == 'explicit-account'


def test_load_nonexistent_file():
    """Test error when config file doesn't exist."""
    with pytest.raises(ConnectionConfigError, match="not found"):
        load_connection_config('snowflake', '/nonexistent/path.yaml')


def test_load_invalid_yaml(tmp_path):
    """Test error with invalid YAML file."""
    config_file = tmp_path / "bad.yaml"
    config_file.write_text("{ invalid yaml [")

    with pytest.raises(ConnectionConfigError, match="Invalid YAML"):
        load_connection_config('snowflake', str(config_file))


def test_load_yaml_not_dict(tmp_path):
    """Test error when YAML is not a dictionary."""
    config_file = tmp_path / "list.yaml"
    config_file.write_text("- item1\n- item2")

    with pytest.raises(ConnectionConfigError, match="dictionary"):
        load_connection_config('snowflake', str(config_file))


def test_get_snowflake_defaults():
    """Test default config for Snowflake."""
    config = load_connection_config('snowflake')

    assert 'account' in config
    assert 'user' in config
    assert 'password' in config
    assert config['warehouse'] == 'COMPUTE_WH'


def test_get_postgres_defaults():
    """Test default config for PostgreSQL."""
    config = load_connection_config('postgres')

    assert config['host'] == 'localhost'
    assert config['port'] == 5432


def test_validate_snowflake_config():
    """Test validation of valid Snowflake config."""
    config = {
        'account': 'test',
        'user': 'user',
        'password': 'pass'
    }

    assert validate_connection_config('snowflake', config) is True


def test_validate_missing_required_field():
    """Test validation fails with missing required field."""
    config = {
        'account': 'test',
        'user': 'user'
        # Missing password
    }

    with pytest.raises(ConnectionConfigError, match="Missing required"):
        validate_connection_config('snowflake', config)


def test_validate_postgres_config():
    """Test validation of PostgreSQL config."""
    config = {
        'host': 'localhost',
        'user': 'user',
        'password': 'pass',
        'database': 'mydb'
    }

    assert validate_connection_config('postgres', config) is True


def test_validate_empty_field():
    """Test validation with empty string field."""
    config = {
        'account': '',
        'user': 'user',
        'password': 'pass'
    }

    with pytest.raises(ConnectionConfigError, match="Missing required"):
        validate_connection_config('snowflake', config)
