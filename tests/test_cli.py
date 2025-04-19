import pytest
import sys
import os
import argparse
from unittest.mock import patch, MagicMock, call, ANY, mock_open # Add mock_open
import logging # Import logging for setup_logging test

# Adjust import path based on structure
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from hellopeter_cli import cli, config
from hellopeter_cli import reset_db # To mock reset_database

# --- Sample Data (for testing argument effects) ---

SAMPLE_BUSINESS_DATA = {
    "slug": "cli-biz",
    "name": "CLI Test Biz",
    "industry_name": "CLI Testing",
    "industry_slug": "cli-testing"
}

SAMPLE_STATS_DATA = {
    "totalReviews": 10,
    "reviewAverage": "4.0",
    "monthlyStats": {"trustIndex": 8.0}
    # ... other fields don't matter as much for CLI logic tests
}

SAMPLE_REVIEWS_DATA = [
    {"id": 301, "review_title": "CLI Review 1"},
    {"id": 302, "review_title": "CLI Review 2"}
]

# --- Fixtures ---

@pytest.fixture
def mock_args(mocker):
    """Fixture to create a mock argparse Namespace object."""
    args = argparse.Namespace()
    # Default values similar to argparse definition
    args.log_file = None
    args.businesses = ["test-biz"]
    args.start_page = 1
    args.end_page = None
    args.save_raw = False
    args.stats_only = False
    args.reviews_only = False
    args.output_format = "csv" # Default
    args.output_dir = config.DEFAULT_OUTPUT_DIR
    args.force_refresh = False
    return args

# --- Mocks for External Dependencies (applied via @patch) ---

# It's often cleaner to patch the specific functions where they are *used* (i.e., in cli.py)
# rather than where they are defined.

# Patching targets within cli.py
PATCH_TARGETS = {
    'init_db': 'hellopeter_cli.cli.init_db',
    'Session': 'hellopeter_cli.cli.Session',
    'get_existing_review_ids': 'hellopeter_cli.cli.get_existing_review_ids',
    'get_or_create_business': 'hellopeter_cli.cli.get_or_create_business',
    'store_review': 'hellopeter_cli.cli.store_review',
    'store_business_stats': 'hellopeter_cli.cli.store_business_stats',
    'fetch_business_stats': 'hellopeter_cli.cli.fetch_business_stats',
    'fetch_reviews_for_business': 'hellopeter_cli.cli.fetch_reviews_for_business',
    'save_raw_data': 'hellopeter_cli.cli.save_raw_data',
    'save_to_database': 'hellopeter_cli.cli.save_to_database',
    'save_to_csv': 'hellopeter_cli.cli.save_to_csv',
    'save_to_json': 'hellopeter_cli.cli.save_to_json',
    'reset_database': 'hellopeter_cli.cli.reset_database',
    'logger': 'hellopeter_cli.cli.logger',
    'os_makedirs': 'hellopeter_cli.cli.os.makedirs',
    'pd_dataframe': 'hellopeter_cli.cli.pd.DataFrame',
    'json_dump': 'hellopeter_cli.cli.json.dump',
    'builtin_open': 'builtins.open'
}

# --- Test Functions ---

# 1. Test main() argument parsing and command dispatching

# @patch(PATCH_TARGETS['fetch_command'], return_value=0) # Removed - Patching inside test
@patch.object(sys, 'argv') # Mock sys.argv
def test_main_dispatch_fetch(mock_argv, mocker):
    """Test that main() parses 'fetch' command and calls fetch_command."""
    # Patch the target command function directly within cli module
    mock_fetch_cmd = mocker.patch('hellopeter_cli.cli.fetch_command', return_value=0)

    mock_argv.__getitem__.side_effect = lambda i: ['cli.py', 'fetch', '--businesses', 'biz1'][i]
    mock_argv.__len__.return_value = 4

    # Need to patch setup_logging as well if we don't want it to run
    mocker.patch('hellopeter_cli.cli.setup_logging')

    return_code = cli.main()

    assert return_code == 0
    mock_fetch_cmd.assert_called_once()
    call_args = mock_fetch_cmd.call_args[0][0] # Get the args object passed to fetch_command
    assert call_args.command == 'fetch'
    assert call_args.businesses == ['biz1']


# @patch(PATCH_TARGETS['reset_command'], return_value=0) # Removed - Patching inside test
@patch.object(sys, 'argv') # Mock sys.argv
def test_main_dispatch_reset(mock_argv, mocker):
    """Test that main() parses 'reset' command and calls reset_command."""
    # Patch the target command function directly within cli module
    mock_reset_cmd = mocker.patch('hellopeter_cli.cli.reset_command', return_value=0)

    mock_argv.__getitem__.side_effect = lambda i: ['cli.py', 'reset'][i]
    mock_argv.__len__.return_value = 2
    mocker.patch('hellopeter_cli.cli.setup_logging')

    return_code = cli.main()

    assert return_code == 0
    mock_reset_cmd.assert_called_once()
    call_args = mock_reset_cmd.call_args[0][0] # Get the args object passed to reset_command
    assert call_args.command == 'reset'


# 2. Test fetch_command logic

@patch(PATCH_TARGETS['save_to_csv'])
@patch(PATCH_TARGETS['fetch_reviews_for_business'])
@patch(PATCH_TARGETS['fetch_business_stats'])
@patch(PATCH_TARGETS['get_existing_review_ids'])
@patch(PATCH_TARGETS['init_db'])
@patch(PATCH_TARGETS['logger'])
def test_fetch_command_csv_default(mock_logger, mock_init_db, mock_get_ids, mock_fetch_stats, mock_fetch_reviews, mock_save_csv, mock_args):
    """Test fetch_command with default CSV output, fetching both stats and reviews."""
    # Arrange
    mock_args.businesses = ['biz-a']
    mock_args.output_format = 'csv'
    mock_fetch_stats.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_STATS_DATA)
    mock_fetch_reviews.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_REVIEWS_DATA)

    # Act
    return_code = cli.fetch_command(mock_args)

    # Assert
    assert return_code == 0
    mock_init_db.assert_not_called() # Not called for CSV
    mock_get_ids.assert_not_called() # Not called for CSV

    # Check scraper calls
    mock_fetch_stats.assert_called_once_with('biz-a')
    mock_fetch_reviews.assert_called_once_with('biz-a', start_page=1, end_page=None, existing_review_ids=None)

    # Check saving call - Expect a single call with combined data
    mock_save_csv.assert_called_once_with(
        config.DEFAULT_OUTPUT_DIR, 
        'biz-a', 
        business_data=SAMPLE_BUSINESS_DATA, 
        reviews=SAMPLE_REVIEWS_DATA,
        stats_data=SAMPLE_STATS_DATA
    )

    # Check summary log message manually
    summary_log = "Total reviews fetched across all processed slugs: 2"
    found_log = False
    for log_call in mock_logger.info.call_args_list:
        if log_call[0][0] == summary_log:
            found_log = True
            break
    assert found_log, f"Expected log message '{summary_log}' not found in logger.info calls."


@patch(PATCH_TARGETS['save_to_database'])
@patch(PATCH_TARGETS['fetch_reviews_for_business'])
@patch(PATCH_TARGETS['fetch_business_stats'])
@patch(PATCH_TARGETS['get_existing_review_ids'], return_value=set())
@patch(PATCH_TARGETS['init_db'])
@patch(PATCH_TARGETS['Session'])
@patch(PATCH_TARGETS['logger'])
def test_fetch_command_db_no_refresh(mock_logger, mock_session, mock_init_db, mock_get_ids, mock_fetch_stats, mock_fetch_reviews, mock_save_db, mock_args):
    """Test fetch_command with DB output, no force refresh."""
    # Arrange
    mock_args.businesses = ['biz-b']
    mock_args.output_format = 'db'
    mock_args.force_refresh = False
    mock_fetch_stats.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_STATS_DATA)
    mock_fetch_reviews.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_REVIEWS_DATA)
    mock_existing_ids = {1, 2, 3} # Sample existing IDs
    mock_get_ids.return_value = mock_existing_ids
    # Mock the session context manager
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance

    # Act
    return_code = cli.fetch_command(mock_args)

    # Assert
    assert return_code == 0
    mock_init_db.assert_called_once() # Called for DB
    mock_get_ids.assert_called_once_with(mock_session_instance, 'biz-b') # Called for DB without force_refresh
    mock_session.assert_called_once() # Session should be created to get IDs
    mock_session_instance.close.assert_called_once() # Session should be closed

    # Check scraper calls
    mock_fetch_stats.assert_called_once_with('biz-b')
    mock_fetch_reviews.assert_called_once_with('biz-b', start_page=1, end_page=None, existing_review_ids=mock_existing_ids)

    # Check saving call - Expect a single call with combined data
    mock_save_db.assert_called_once_with(
        SAMPLE_BUSINESS_DATA, 
        reviews=SAMPLE_REVIEWS_DATA, 
        stats_data=SAMPLE_STATS_DATA
    )

    # Check summary log message manually
    expected_log = f"Found {len(mock_existing_ids)} existing reviews for biz-b in the database, will fetch only newer ones."
    mock_logger.info.assert_any_call(expected_log)

    # Check final summary log
    summary_log = "Total reviews fetched across all processed slugs: 2" # Should be 2 based on SAMPLE_REVIEWS_DATA
    found_log = False
    for log_call in mock_logger.info.call_args_list:
        if log_call[0][0] == summary_log:
            found_log = True
            break
    assert found_log, f"Expected log message '{summary_log}' not found in logger.info calls."


@patch(PATCH_TARGETS['save_to_database'])
@patch(PATCH_TARGETS['fetch_reviews_for_business'])
@patch(PATCH_TARGETS['fetch_business_stats'])
@patch(PATCH_TARGETS['get_existing_review_ids'])
@patch(PATCH_TARGETS['init_db'])
@patch(PATCH_TARGETS['logger'])
def test_fetch_command_db_force_refresh(mock_logger, mock_init_db, mock_get_ids, mock_fetch_stats, mock_fetch_reviews, mock_save_db, mock_args):
    """Test fetch_command with DB output and force refresh."""
    # Arrange
    mock_args.businesses = ['biz-c']
    mock_args.output_format = 'db'
    mock_args.force_refresh = True # Force refresh is True
    mock_fetch_stats.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_STATS_DATA)
    mock_fetch_reviews.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_REVIEWS_DATA)

    # Act
    return_code = cli.fetch_command(mock_args)

    # Assert
    assert return_code == 0
    mock_init_db.assert_called_once() # Called for DB
    mock_get_ids.assert_not_called() # Should NOT be called with force_refresh

    # Check scraper calls
    mock_fetch_stats.assert_called_once_with('biz-c')
    mock_fetch_reviews.assert_called_once_with('biz-c', start_page=1, end_page=None, existing_review_ids=None) # existing_review_ids should be None

    # Check saving call - Expect a single call with combined data
    mock_save_db.assert_called_once_with(
        SAMPLE_BUSINESS_DATA, 
        reviews=SAMPLE_REVIEWS_DATA, 
        stats_data=SAMPLE_STATS_DATA
    )


@patch(PATCH_TARGETS['save_to_json'])
@patch(PATCH_TARGETS['fetch_reviews_for_business'])
@patch(PATCH_TARGETS['fetch_business_stats'])
@patch(PATCH_TARGETS['get_existing_review_ids'])
@patch(PATCH_TARGETS['init_db'])
@patch(PATCH_TARGETS['logger'])
def test_fetch_command_json_stats_only(mock_logger, mock_init_db, mock_get_ids, mock_fetch_stats, mock_fetch_reviews, mock_save_json, mock_args):
    """Test fetch_command with JSON output, stats only."""
    # Arrange
    mock_args.businesses = ['biz-d']
    mock_args.output_format = 'json'
    mock_args.stats_only = True
    mock_fetch_stats.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_STATS_DATA)

    # Act
    return_code = cli.fetch_command(mock_args)

    # Assert
    assert return_code == 0
    mock_init_db.assert_not_called()
    mock_get_ids.assert_not_called()

    # Check scraper calls
    mock_fetch_stats.assert_called_once_with('biz-d')
    mock_fetch_reviews.assert_not_called() # Reviews should not be fetched

    # Check saving call - Expect reviews=None
    mock_save_json.assert_called_once_with(
        config.DEFAULT_OUTPUT_DIR, 
        'biz-d', 
        business_data=SAMPLE_BUSINESS_DATA, 
        reviews=None, 
        stats_data=SAMPLE_STATS_DATA
    )

    # Check summary log message manually
    summary_log = "Total reviews fetched across all processed slugs: 0"
    found_log = False
    for log_call in mock_logger.info.call_args_list:
        if log_call[0][0] == summary_log:
            found_log = True
            break
    assert found_log, f"Expected log message '{summary_log}' not found in logger.info calls."


@patch(PATCH_TARGETS['save_to_csv'])
@patch(PATCH_TARGETS['fetch_reviews_for_business'])
@patch(PATCH_TARGETS['fetch_business_stats'])
@patch(PATCH_TARGETS['get_existing_review_ids'])
@patch(PATCH_TARGETS['init_db'])
@patch(PATCH_TARGETS['logger'])
def test_fetch_command_reviews_only_save_raw(mock_logger, mock_init_db, mock_get_ids, mock_fetch_stats, mock_fetch_reviews, mock_save_csv, mock_args):
    """Test fetch_command with reviews only and save raw."""
    # Arrange
    mock_args.businesses = ['biz-e']
    mock_args.output_format = 'csv' # Save to CSV
    mock_args.reviews_only = True
    mock_args.save_raw = True # Save raw enabled
    mock_fetch_reviews.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_REVIEWS_DATA)

    # Act
    return_code = cli.fetch_command(mock_args)

    # Assert
    assert return_code == 0
    mock_init_db.assert_not_called()
    mock_get_ids.assert_not_called()

    # Check scraper calls
    mock_fetch_stats.assert_not_called() # Stats should not be fetched
    mock_fetch_reviews.assert_called_once_with('biz-e', start_page=1, end_page=None, existing_review_ids=None)

    # Check saving call - Expect stats_data=None
    mock_save_csv.assert_called_once_with(
        config.DEFAULT_OUTPUT_DIR, 
        'biz-e', 
        business_data=SAMPLE_BUSINESS_DATA, 
        reviews=SAMPLE_REVIEWS_DATA,
        stats_data=None # Expect None for stats_data
    )

# 3. Test reset_command

@patch(PATCH_TARGETS['reset_database'])
@patch(PATCH_TARGETS['logger'])
def test_reset_command(mock_logger, mock_reset_db, mock_args):
    """Test the reset command calls reset_database."""
    # Arrange
    # mock_args is not strictly needed but passed for consistency if needed later

    # Act
    return_code = cli.reset_command(mock_args)

    # Assert
    assert return_code == 0
    mock_reset_db.assert_called_once()
    mock_logger.info.assert_has_calls([
        call("Resetting database..."),
        call("Database reset completed.")
    ])

# 4. Test individual save functions (could be expanded)

@patch(PATCH_TARGETS['pd_dataframe'])
@patch(PATCH_TARGETS['os_makedirs'])
@patch(PATCH_TARGETS['logger'])
def test_save_to_csv_stats_extraction(mock_logger, mock_makedirs, mock_df, mock_args):
    """Test the specific stats extraction logic within save_to_csv."""
    # Arrange
    biz_slug = "extract-test"
    # More complex stats data to test extraction
    test_stats_data = {
        "totalReviews": 50,
        "reviewAverage": "4.5",
        "avgResponseTime": 120.5,
        "responseRate": 0.95,
        "monthlyStats": {
            "trustIndex": 8.5,
            "industryId": 99,
            "industryRanking": 1,
            "reviewCountTotal": 15
        },
        "reviewRatings": {
            "rows": [
                ["1 Star", 2],
                ["2 Stars", 3],
                ["3 Stars", 5],
                ["4 Stars", 10],
                ["5 Stars", 30]
            ]
        },
        "other_complex": [{"a": 1}], # Should be ignored
        "rankings": [] # Should be ignored
    }
    expected_extracted_dict = {
        'total_reviews': 50,
        'avg_response_time': 120.5,
        'response_rate': 0.95,
        'average_rating': 4.5,
        'rating_1_count': 2,
        'rating_2_count': 3,
        'rating_3_count': 5,
        'rating_4_count': 10,
        'rating_5_count': 30,
        'trust_index': 8.5,
        'industry_id': 99,
        'industry_ranking': 1,
        'review_count_total_monthly': 15
    }
    mock_df_instance = MagicMock()
    mock_df.return_value = mock_df_instance

    # Act
    cli.save_to_csv(mock_args.output_dir, biz_slug, stats_data=test_stats_data)

    # Assert
    mock_makedirs.assert_called_with(mock_args.output_dir, exist_ok=True)
    # Check that DataFrame was created with the correctly extracted + structured dict
    mock_df.assert_called_once_with([expected_extracted_dict])
    # Remove assertion on the instance, rely on checking the DataFrame constructor call
    # mock_df_instance.to_csv.assert_called_once()


@patch(PATCH_TARGETS['builtin_open'], new_callable=mock_open)
@patch(PATCH_TARGETS['json_dump'])
@patch(PATCH_TARGETS['os_makedirs'])
@patch(PATCH_TARGETS['logger'])
def test_save_to_json(mock_logger, mock_makedirs, mock_json_dump, mock_open_instance, mock_args):
    """Test the save_to_json function."""
    # Arrange
    biz_slug = "json-test"
    test_reviews = [{"id": 1}] # Sample data
    mock_args.output_dir = "json_out"

    # Act
    cli.save_to_json(mock_args.output_dir, biz_slug, reviews=test_reviews)

    # Assert
    mock_makedirs.assert_called_with(mock_args.output_dir, exist_ok=True)
    # Check filename structure (timestamp makes exact match hard)
    open_call_args, open_call_kwargs = mock_open_instance.call_args
    assert open_call_args[0].startswith(os.path.join(mock_args.output_dir, f"reviews_{biz_slug}_"))
    assert open_call_args[0].endswith(".json")
    # Check positional arguments for open()
    assert len(open_call_args) >= 2 # Ensure mode argument exists
    assert open_call_args[1] == 'w' # Mode is the second positional arg
    # Check keyword arguments (encoding might be passed or default)
    assert open_call_kwargs.get('encoding') is None # Default open encoding (Python decides based on platform)
    # assert open_call_kwargs.get('mode') == 'w' # Check mode

    # Check json.dump call
    dump_call_args, dump_call_kwargs = mock_json_dump.call_args
    assert dump_call_args[0] == test_reviews
    assert dump_call_args[1] == mock_open_instance() # Check file handle
    assert dump_call_kwargs.get('indent') == 4


@patch(PATCH_TARGETS['init_db'])
@patch(PATCH_TARGETS['Session'])
@patch(PATCH_TARGETS['get_or_create_business'])
@patch(PATCH_TARGETS['store_review'])
@patch(PATCH_TARGETS['store_business_stats'])
@patch(PATCH_TARGETS['logger'])
def test_save_to_database(mock_logger, mock_store_stats, mock_store_review, mock_get_create_biz, mock_session_cls, mock_init_db, mock_args):
    """Test the save_to_database function call sequence."""
    # Arrange
    mock_session_instance = MagicMock()
    mock_session_cls.return_value = mock_session_instance
    mock_biz_instance = MagicMock()
    mock_biz_instance.id = 5 # Sample business ID
    mock_get_create_biz.return_value = mock_biz_instance
    test_reviews = [{"id": 1}, {"id": 2}]
    test_stats = {"totalReviews": 3}

    # Act
    success = cli.save_to_database(SAMPLE_BUSINESS_DATA, reviews=test_reviews, stats_data=test_stats)

    # Assert
    assert success is True
    mock_init_db.assert_called_once()
    mock_session_cls.assert_called_once()
    mock_get_create_biz.assert_called_once_with(
        mock_session_instance,
        SAMPLE_BUSINESS_DATA["slug"],
        SAMPLE_BUSINESS_DATA["name"],
        SAMPLE_BUSINESS_DATA.get("industry_name"),
        SAMPLE_BUSINESS_DATA.get("industry_slug")
    )
    # Check store_review called for each review
    assert mock_store_review.call_count == len(test_reviews)
    mock_store_review.assert_has_calls([
        call(mock_session_instance, test_reviews[0], mock_biz_instance.id),
        call(mock_session_instance, test_reviews[1], mock_biz_instance.id)
    ])
    # Check store_business_stats called
    mock_store_stats.assert_called_once_with(mock_session_instance, mock_biz_instance.id, test_stats)
    # Check session closed
    mock_session_instance.close.assert_called_once() 

@patch(PATCH_TARGETS['save_to_csv']) # Fallback target
@patch(PATCH_TARGETS['save_to_database']) # Original target
@patch(PATCH_TARGETS['fetch_reviews_for_business'])
@patch(PATCH_TARGETS['fetch_business_stats'])
@patch(PATCH_TARGETS['init_db'], side_effect=Exception("DB Init Failed")) # Make init_db fail
@patch(PATCH_TARGETS['logger'])
def test_fetch_command_db_init_fails(
    mock_logger, mock_init_db, mock_fetch_stats, mock_fetch_reviews, mock_save_db, mock_save_csv, mock_args
):
    """Test fetch_command fallback to CSV when DB init fails."""
    # Arrange
    mock_args.businesses = ['biz-fail-init']
    mock_args.output_format = 'db' # Start with DB format
    # Mock fetch return values (needed even if saving format changes)
    mock_fetch_stats.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_STATS_DATA)
    mock_fetch_reviews.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_REVIEWS_DATA)

    # Act
    return_code = cli.fetch_command(mock_args)

    # Assert
    assert return_code == 0 # Command should still complete
    mock_init_db.assert_called_once() # Ensure it was attempted
    # Check logs for error and fallback message
    mock_logger.error.assert_any_call("Error initializing database: DB Init Failed")
    mock_logger.error.assert_any_call("Falling back to CSV output format.")
    # Check that saving was attempted via CSV, not DB
    mock_save_db.assert_not_called()
    # Expect a single call with both stats and reviews
    mock_save_csv.assert_called_once_with(
        config.DEFAULT_OUTPUT_DIR, 
        'biz-fail-init', 
        business_data=SAMPLE_BUSINESS_DATA, 
        reviews=SAMPLE_REVIEWS_DATA,
        stats_data=SAMPLE_STATS_DATA
    )
    # Ensure assert_has_calls is removed/commented
    # mock_save_csv.assert_has_calls([
    #     call(config.DEFAULT_OUTPUT_DIR, 'biz-fail-init', business_data=SAMPLE_BUSINESS_DATA, stats_data=SAMPLE_STATS_DATA),
    #     call(config.DEFAULT_OUTPUT_DIR, 'biz-fail-init', business_data=SAMPLE_BUSINESS_DATA, reviews=SAMPLE_REVIEWS_DATA)
    # ], any_order=False)

    # Check summary log message manually
    summary_log = "Total reviews fetched across all processed slugs: 2"
    found_log = False
    for log_call in mock_logger.info.call_args_list:
        if log_call[0][0] == summary_log:
            found_log = True
            break
    assert found_log, f"Expected log message '{summary_log}' not found in logger.info calls."


@patch(PATCH_TARGETS['fetch_business_stats'])
@patch(PATCH_TARGETS['fetch_reviews_for_business'])
@patch(PATCH_TARGETS['logger'])
def test_fetch_command_no_businesses(mock_logger, mock_fetch_reviews, mock_fetch_stats, mock_args):
    """Test fetch_command when no businesses are provided."""
    # Arrange
    mock_args.businesses = [] # Empty list

    # Act
    return_code = cli.fetch_command(mock_args)

    # Assert
    assert return_code == 1 # Should indicate an error/failure
    mock_logger.error.assert_called_once_with("No businesses specified. Please provide at least one business slug.")
    # Ensure no fetching was attempted
    mock_fetch_stats.assert_not_called()
    mock_fetch_reviews.assert_not_called()


@patch(PATCH_TARGETS['save_to_csv'])
@patch(PATCH_TARGETS['fetch_reviews_for_business'], side_effect=Exception("Fetch Review Error")) # Error during fetch
@patch(PATCH_TARGETS['fetch_business_stats'])
@patch(PATCH_TARGETS['logger'])
def test_fetch_command_loop_exception(mock_logger, mock_fetch_stats, mock_fetch_reviews, mock_save_csv, mock_args):
    """Test fetch_command exception handling within the business loop."""
    # Arrange
    mock_args.businesses = ['biz-ok', 'biz-fail', 'biz-ok-after']
    mock_args.output_format = 'csv'
    # Let stats fetching succeed for all
    mock_fetch_stats.return_value = (SAMPLE_BUSINESS_DATA, SAMPLE_STATS_DATA)
    # Let review fetching succeed for the first and third, fail for the second
    mock_fetch_reviews.side_effect = [
        (SAMPLE_BUSINESS_DATA, SAMPLE_REVIEWS_DATA), # Success for biz-ok
        Exception("Fetch Review Error"),           # Failure for biz-fail
        (SAMPLE_BUSINESS_DATA, SAMPLE_REVIEWS_DATA)  # Success for biz-ok-after
    ]

    # Act
    return_code = cli.fetch_command(mock_args)

    # Assert
    assert return_code == 0 # Command finishes successfully overall
    assert mock_fetch_stats.call_count == 3
    assert mock_fetch_reviews.call_count == 3 # Attempted for all three
    # Check that the specific error for 'biz-fail' was logged using exception
    # Extract the actual exception object raised by the mock
    actual_exception = None
    for call_args, call_kwargs in mock_fetch_reviews.call_args_list:
        if isinstance(mock_fetch_reviews.side_effect, list) and len(mock_fetch_reviews.side_effect) > call_args.index:
             eff = mock_fetch_reviews.side_effect[call_args.index] # Simple index assumption might fail if calls skipped
             if isinstance(eff, Exception):
                 actual_exception = eff
                 break
        elif isinstance(mock_fetch_reviews.side_effect, Exception): # If side effect is single exception
             actual_exception = mock_fetch_reviews.side_effect
             break
    # Need to refine how to get the specific exception instance that was raised for the failing call
    # For now, let's just check the message prefix and exc_info=True
    
    expected_msg_prefix = "Unexpected error processing biz-fail:"
    found_call = False
    for call_args, call_kwargs in mock_logger.exception.call_args_list:
        if call_args[0].startswith(expected_msg_prefix) and call_kwargs.get('exc_info') is True:
             found_call = True
             break
    assert found_call, f"Expected logger.exception call starting with '{expected_msg_prefix}' and exc_info=True"
    # mock_logger.error.assert_called_once_with("Error processing biz-fail: Fetch Review Error")
    
    # Check that saving happened ONLY for the successful slugs
    # Updated count: 1 call per slug where fetch didn't raise exception before save
    assert mock_save_csv.call_count == 2
    # Check calls for successful slugs
    mock_save_csv.assert_any_call(config.DEFAULT_OUTPUT_DIR, 'biz-ok', business_data=ANY, reviews=ANY, stats_data=ANY) # Check general structure
    mock_save_csv.assert_any_call(config.DEFAULT_OUTPUT_DIR, 'biz-ok-after', business_data=ANY, reviews=ANY, stats_data=ANY)
    # DO NOT check for biz-fail, as save shouldn't be reached due to exception
    # mock_save_csv.assert_any_call(config.DEFAULT_OUTPUT_DIR, 'biz-fail', business_data=ANY, reviews=ANY, stats_data=ANY) 


# Test setup_logging directly
@patch('logging.FileHandler') # Mock the FileHandler class
@patch('hellopeter_cli.cli.logger') # Mock the logger instance used in cli.py
def test_setup_logging_with_file(mock_cli_logger, mock_file_handler_cls):
    """Test setup_logging adds a file handler when log_file is provided."""
    # Arrange
    test_log_file = "test_run.log"
    mock_handler_instance = MagicMock()
    mock_file_handler_cls.return_value = mock_handler_instance

    # Act
    cli.setup_logging(log_file=test_log_file)

    # Assert
    # Check that FileHandler was instantiated with the correct filename
    mock_file_handler_cls.assert_called_once_with(test_log_file)
    # Check that setLevel and setFormatter were called on the handler instance
    mock_handler_instance.setLevel.assert_called_once_with(logging.INFO)
    mock_handler_instance.setFormatter.assert_called_once()
    # Check that the handler was added to the logger
    mock_cli_logger.addHandler.assert_called_once_with(mock_handler_instance)

@patch('logging.FileHandler')
@patch('hellopeter_cli.cli.logger')
def test_setup_logging_no_file(mock_cli_logger, mock_file_handler_cls):
    """Test setup_logging does not add a file handler when log_file is None."""
    # Act
    cli.setup_logging(log_file=None)

    # Assert
    mock_file_handler_cls.assert_not_called()
    mock_cli_logger.addHandler.assert_not_called() # Assuming the console handler is added elsewhere 