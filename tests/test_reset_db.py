import pytest
import os
from unittest.mock import patch, MagicMock, call

# Adjust import path based on structure
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import the function to test
from hellopeter_cli import reset_db

# Patch targets within reset_db.py
CONFIG_PATH = 'hellopeter_cli.reset_db.config'
OS_PATH_EXISTS = 'hellopeter_cli.reset_db.os.path.exists'
OS_REMOVE = 'hellopeter_cli.reset_db.os.remove'
SESSION_CLOSE_ALL = 'hellopeter_cli.reset_db.Session.close_all'
BASE_CREATE_ALL = 'hellopeter_cli.reset_db.Base.metadata.create_all'
LOGGER = 'hellopeter_cli.reset_db.logger'
ENGINE = 'hellopeter_cli.reset_db.engine' # Needed for create_all

# --- Test Functions ---

@patch(BASE_CREATE_ALL)
@patch(OS_REMOVE)
@patch(SESSION_CLOSE_ALL)
@patch(OS_PATH_EXISTS, return_value=True) # Simulate file existing
@patch(CONFIG_PATH)
@patch(LOGGER)
def test_reset_database_file_exists_success(
    mock_logger, mock_config, mock_exists, mock_close_all, mock_remove, mock_create_all
):
    """Test reset_database when the SQLite file exists and removal succeeds."""
    # Arrange
    test_db_path = "/fake/path/test.db"
    mock_config.DEFAULT_DB_PATH = test_db_path
    mock_engine_instance = MagicMock() # Mock engine needed for create_all

    # Act
    # Patch the engine directly in the module where create_all uses it
    with patch(ENGINE, mock_engine_instance):
        success = reset_db.reset_database()

    # Assert
    assert success is True
    mock_exists.assert_called_once_with(test_db_path)
    mock_logger.info.assert_any_call(f"Removing SQLite database file: {test_db_path}")
    mock_close_all.assert_called_once()
    mock_remove.assert_called_once_with(test_db_path)
    mock_logger.info.assert_any_call(f"SQLite database file removed.")
    mock_create_all.assert_called_once_with(mock_engine_instance)
    mock_logger.info.assert_any_call("Creating all tables...")
    mock_logger.info.assert_any_call("All tables created successfully.")
    mock_logger.info.assert_any_call("Database reset completed successfully.")


@patch(BASE_CREATE_ALL)
@patch(OS_REMOVE)
@patch(SESSION_CLOSE_ALL)
@patch(OS_PATH_EXISTS, return_value=False) # Simulate file NOT existing
@patch(CONFIG_PATH)
@patch(LOGGER)
def test_reset_database_file_not_exist(
    mock_logger, mock_config, mock_exists, mock_close_all, mock_remove, mock_create_all
):
    """Test reset_database when the SQLite file does not exist."""
    # Arrange
    test_db_path = "/fake/path/other.db"
    mock_config.DEFAULT_DB_PATH = test_db_path
    mock_engine_instance = MagicMock()

    # Act
    with patch(ENGINE, mock_engine_instance):
        success = reset_db.reset_database()

    # Assert
    assert success is True
    mock_exists.assert_called_once_with(test_db_path)
    # Ensure removal steps were NOT called
    # The log message is inside the `if exists` block, so it shouldn't be called here
    # mock_logger.info.assert_any_call(f"Removing SQLite database file: {test_db_path}") # Incorrect assertion removed
    mock_close_all.assert_not_called()
    mock_remove.assert_not_called()
    # Ensure creation still happens
    mock_create_all.assert_called_once_with(mock_engine_instance)
    mock_logger.info.assert_any_call("Creating all tables...")
    mock_logger.info.assert_any_call("All tables created successfully.")
    mock_logger.info.assert_any_call("Database reset completed successfully.")


@patch(BASE_CREATE_ALL)
@patch(OS_REMOVE, side_effect=OSError("Permission denied")) # Simulate remove error
@patch(SESSION_CLOSE_ALL)
@patch(OS_PATH_EXISTS, return_value=True) # Simulate file existing
@patch(CONFIG_PATH)
@patch(LOGGER)
def test_reset_database_remove_error(
    mock_logger, mock_config, mock_exists, mock_close_all, mock_remove, mock_create_all
):
    """Test reset_database when os.remove fails."""
    # Arrange
    test_db_path = "/fake/path/locked.db"
    mock_config.DEFAULT_DB_PATH = test_db_path
    mock_engine_instance = MagicMock()

    # Act
    # No need to patch engine here as create_all won't be reached
    success = reset_db.reset_database()

    # Assert
    assert success is False # Function should return False on error
    mock_exists.assert_called_once_with(test_db_path)
    mock_logger.info.assert_any_call(f"Removing SQLite database file: {test_db_path}")
    mock_close_all.assert_called_once() # Close is attempted before remove
    mock_remove.assert_called_once_with(test_db_path)
    mock_logger.error.assert_called_once() # Check error was logged
    assert "Error removing SQLite database file:" in mock_logger.error.call_args[0][0]
    mock_create_all.assert_not_called() # Should not proceed to create tables 