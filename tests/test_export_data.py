import pytest
import os
import pandas as pd
from unittest.mock import patch, MagicMock, call
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession

# Adjust import path based on structure
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import functions/objects to test and dependencies
from hellopeter_cli import export_data, config
from hellopeter_cli.database import Base, Business, Review, BusinessStats # For setting up DB

# --- Fixtures ---

@pytest.fixture(scope="function")
def populated_db_session() -> SQLAlchemySession:
    """Fixture for creating and populating an in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine) # Create tables

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # --- Add Sample Data ---
    biz1 = Business(slug="biz-a", name="Business A", industry_name="Testing")
    biz2 = Business(slug="biz-b", name="Business B", industry_name="Testing")
    session.add_all([biz1, biz2])
    session.commit() # Commit to get IDs

    rev1 = Review(business_id=biz1.id, review_id=101, review_title="Review 1A", review_rating=5)
    rev2 = Review(business_id=biz1.id, review_id=102, review_title="Review 2A", review_rating=4)
    rev3 = Review(business_id=biz2.id, review_id=103, review_title="Review 1B", review_rating=3)
    session.add_all([rev1, rev2, rev3])

    stats1 = BusinessStats(business_id=biz1.id, total_reviews=2, average_rating=4.5)
    stats2 = BusinessStats(business_id=biz2.id, total_reviews=1, average_rating=3.0)
    session.add_all([stats1, stats2])

    session.commit()
    # --- End Sample Data ---

    # Monkeypatch the engine used by the export_data module to use our in-memory engine
    # This ensures the export functions query the test DB
    with patch('hellopeter_cli.export_data.engine', engine):
        try:
            yield session
        finally:
            session.close()
            Base.metadata.drop_all(engine) # Clean up tables after test


# --- Test Functions ---

@patch('hellopeter_cli.export_data.os.makedirs')
@patch('pandas.DataFrame.to_csv') # Patch the to_csv method
@patch('pandas.read_sql') # Patch read_sql to control the DataFrame returned
def test_export_businesses(mock_read_sql, mock_to_csv, mock_makedirs, populated_db_session):
    """Test exporting all businesses."""
    # Arrange
    # Simulate read_sql returning a DataFrame (content doesn't strictly matter here)
    mock_df = MagicMock(spec=pd.DataFrame)
    mock_read_sql.return_value = mock_df
    output_dir = "test_output_businesses"
    expected_file = os.path.join(output_dir, "businesses.csv")

    # Act
    result_file = export_data.export_businesses(output_dir=output_dir)

    # Assert
    assert result_file == expected_file
    mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
    mock_read_sql.assert_called_once() # Check it tried to read
    # Check the SQL query text passed to read_sql
    sql_query_arg = mock_read_sql.call_args[0][0]
    assert "select" in str(sql_query_arg).lower()
    assert "from businesses" in str(sql_query_arg).lower()
    # Check that to_csv was called on the mock DataFrame
    mock_df.to_csv.assert_called_once_with(expected_file, index=False)


@patch('hellopeter_cli.export_data.os.makedirs')
@patch('pandas.DataFrame.to_csv')
@patch('pandas.read_sql')
def test_export_reviews_all(mock_read_sql, mock_to_csv, mock_makedirs, populated_db_session):
    """Test exporting all reviews when no business_slug is specified."""
    # Arrange
    mock_df = MagicMock(spec=pd.DataFrame)
    mock_read_sql.return_value = mock_df
    output_dir = "test_output_reviews_all"
    expected_file = os.path.join(output_dir, "reviews.csv")

    # Act
    result_file = export_data.export_reviews(output_dir=output_dir) # No slug

    # Assert
    assert result_file == expected_file
    mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
    mock_read_sql.assert_called_once()
    # Check the SQL query text
    sql_query_arg = mock_read_sql.call_args[0][0]
    assert "select" in str(sql_query_arg).lower()
    assert "from reviews" in str(sql_query_arg).lower()
    assert "where" not in str(sql_query_arg).lower() # Ensure no WHERE clause for slug
    # Check to_csv call
    mock_df.to_csv.assert_called_once_with(expected_file, index=False)


@patch('hellopeter_cli.export_data.os.makedirs')
@patch('pandas.DataFrame.to_csv')
@patch('pandas.read_sql')
def test_export_reviews_specific_business(mock_read_sql, mock_to_csv, mock_makedirs, populated_db_session):
    """Test exporting reviews for a specific business."""
    # Arrange
    mock_df = MagicMock(spec=pd.DataFrame)
    mock_read_sql.return_value = mock_df
    business_slug = "biz-a"
    output_dir = "test_output_reviews_specific"
    expected_file = os.path.join(output_dir, f"reviews_{business_slug}.csv")

    # Act
    result_file = export_data.export_reviews(business_slug=business_slug, output_dir=output_dir)

    # Assert
    assert result_file == expected_file
    mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
    mock_read_sql.assert_called_once()
    # Check the SQL query text
    sql_query_arg = mock_read_sql.call_args[0][0]
    assert "select r.* from reviews r" in str(sql_query_arg).lower()
    assert "join businesses b" in str(sql_query_arg).lower()
    assert "where b.slug = :slug" in str(sql_query_arg).lower()
    # Check the params passed to read_sql
    params_arg = mock_read_sql.call_args.kwargs.get('params') or (mock_read_sql.call_args[0][2] if len(mock_read_sql.call_args[0]) > 2 else None) # Handle positional/keyword params
    assert params_arg == {"slug": business_slug}
    # Check to_csv call
    mock_df.to_csv.assert_called_once_with(expected_file, index=False)


@patch('hellopeter_cli.export_data.os.makedirs')
@patch('pandas.DataFrame.to_csv')
@patch('pandas.read_sql')
def test_export_business_stats_all(mock_read_sql, mock_to_csv, mock_makedirs, populated_db_session):
    """Test exporting stats for all businesses."""
    # Arrange
    mock_df = MagicMock(spec=pd.DataFrame)
    mock_read_sql.return_value = mock_df
    output_dir = "test_output_stats_all"
    expected_file = os.path.join(output_dir, "business_stats.csv")

    # Act
    result_file = export_data.export_business_stats(output_dir=output_dir) # No slug

    # Assert
    assert result_file == expected_file
    mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
    mock_read_sql.assert_called_once()
    # Check the SQL query text
    sql_query_arg = mock_read_sql.call_args[0][0]
    assert "select bs.*, b.name, b.slug from business_stats bs" in str(sql_query_arg).lower()
    assert "join businesses b" in str(sql_query_arg).lower()
    assert "where" not in str(sql_query_arg).lower()
    # Check to_csv call
    mock_df.to_csv.assert_called_once_with(expected_file, index=False)


@patch('hellopeter_cli.export_data.os.makedirs')
@patch('pandas.DataFrame.to_csv')
@patch('pandas.read_sql')
def test_export_business_stats_specific(mock_read_sql, mock_to_csv, mock_makedirs, populated_db_session):
    """Test exporting stats for a specific business."""
    # Arrange
    mock_df = MagicMock(spec=pd.DataFrame)
    mock_read_sql.return_value = mock_df
    business_slug = "biz-b"
    output_dir = "test_output_stats_specific"
    expected_file = os.path.join(output_dir, f"business_stats_{business_slug}.csv")

    # Act
    result_file = export_data.export_business_stats(business_slug=business_slug, output_dir=output_dir)

    # Assert
    assert result_file == expected_file
    mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
    mock_read_sql.assert_called_once()
    # Check the SQL query text
    sql_query_arg = mock_read_sql.call_args[0][0]
    assert "select bs.* from business_stats bs" in str(sql_query_arg).lower()
    assert "join businesses b" in str(sql_query_arg).lower()
    assert "where b.slug = :slug" in str(sql_query_arg).lower()
    # Check the params passed to read_sql
    params_arg = mock_read_sql.call_args.kwargs.get('params') or (mock_read_sql.call_args[0][2] if len(mock_read_sql.call_args[0]) > 2 else None)
    assert params_arg == {"slug": business_slug}
    # Check to_csv call
    mock_df.to_csv.assert_called_once_with(expected_file, index=False) 