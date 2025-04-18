import pytest
import requests
import requests_mock
import time
import json
import os
from unittest.mock import patch, call, Mock, mock_open # Import mock_open

# Adjust import path based on structure
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from hellopeter_cli import config # Need config for URLs and constants
from hellopeter_cli.hellopeter_scraper import (
    make_api_request,
    get_total_pages,
    fetch_business_stats,
    fetch_reviews_for_business,
    save_raw_data
)

# --- Sample Data ---

BUSINESS_SLUG = "test-scraper-biz"

BASE_REVIEWS_URL = f"{config.BASE_API_URL}/{BUSINESS_SLUG}/{config.REVIEWS_ENDPOINT}"
BASE_STATS_URL = f"{config.BUSINESS_STATS_BASE_URL}/{BUSINESS_SLUG}"

# Sample API Responses
SAMPLE_REVIEWS_PAGE_1 = {
    "current_page": 1,
    "data": [
        {"id": 201, "review_title": "Scraper Review 1", "business_name": "Scraper Biz", "industry_name": "Scraping", "industry_slug": "scraping"},
        {"id": 202, "review_title": "Scraper Review 2", "business_name": "Scraper Biz"}
    ],
    "first_page_url": "...",
    "from": 1,
    "last_page": 2,
    "last_page_url": "...",
    "next_page_url": "...",
    "path": "...",
    "per_page": 10,
    "prev_page_url": None,
    "to": 2,
    "total": 12
}

SAMPLE_REVIEWS_PAGE_2 = {
    "current_page": 2,
    "data": [
        {"id": 203, "review_title": "Scraper Review 3", "business_name": "Scraper Biz"},
        {"id": 204, "review_title": "Scraper Review 4", "business_name": "Scraper Biz"}
    ],
    "first_page_url": "...",
    "from": 3,
    "last_page": 2,
    "last_page_url": "...",
    "next_page_url": None,
    "path": "...",
    "per_page": 10,
    "prev_page_url": "...",
    "to": 4,
    "total": 12
}

SAMPLE_STATS_RESPONSE = {
    "totalReviews": 12,
    "reviewAverage": "3.5",
    "avgResponseTime": 90.0,
    "responseRate": 0.8,
    "monthlyStats": {
        "businessName": "Scraper Biz Full Name",
        "trustIndex": 7.0,
        "industryId": 101,
        "industryName": "Scraping Industry",
        "industrySlug": "scraping-industry",
        "industryRanking": 5,
        "reviewCountTotal": 12
    },
    "reviewRatings": {
        "rows": [["1 Star", 1], ["5 Stars", 5]]
    }
}


# --- Test Functions ---

@patch('time.sleep', return_value=None) # Mock time.sleep to speed up tests
def test_make_api_request_success(mock_sleep, requests_mock):
    """Test successful API request with mocking."""
    test_url = "http://test.com/api/data"
    expected_response = {"success": True, "data": [1, 2, 3]}
    requests_mock.get(test_url, json=expected_response, status_code=200)

    # Act
    response = make_api_request(test_url)

    # Assert
    assert response == expected_response
    assert requests_mock.call_count == 1
    history = requests_mock.request_history
    assert history[0].url == test_url
    assert history[0].method == "GET"
    mock_sleep.assert_called_once_with(config.REQUEST_DELAY)


@patch('time.sleep', return_value=None)
def test_make_api_request_http_error(mock_sleep, requests_mock):
    """Test that HTTP errors raise exceptions (backoff not tested here)."""
    test_url = "http://test.com/api/error"
    requests_mock.get(test_url, status_code=500, reason="Server Error")

    # Act & Assert
    with pytest.raises(requests.exceptions.HTTPError):
        make_api_request(test_url)

    # Check sleep was called (might be more than once due to backoff)
    # mock_sleep.assert_called_once_with(config.REQUEST_DELAY)
    assert mock_sleep.called # Check that sleep was called at least once


@patch('hellopeter_cli.hellopeter_scraper.make_api_request')
def test_get_total_pages_success(mock_make_request):
    """Test getting total pages successfully."""
    # Arrange
    mock_make_request.return_value = SAMPLE_REVIEWS_PAGE_1 # Contains "last_page": 2
    expected_url = BASE_REVIEWS_URL
    expected_params = {"page": 1, "count": 10}

    # Act
    total_pages = get_total_pages(BUSINESS_SLUG)

    # Assert
    assert total_pages == 2
    mock_make_request.assert_called_once() # Check it was called
    args, kwargs = mock_make_request.call_args
    assert args == (expected_url, expected_params) # Both url and params are positional args
    assert kwargs == {} # No keyword args expected


@patch('hellopeter_cli.hellopeter_scraper.make_api_request')
@patch('hellopeter_cli.hellopeter_scraper.logger') # Mock logger
def test_get_total_pages_not_found(mock_logger, mock_make_request):
    """Test get_total_pages when business is not found (404)."""
    # Arrange
    mock_response = requests.Response()
    mock_response.status_code = 404
    mock_make_request.side_effect = requests.exceptions.HTTPError(response=mock_response)

    # Act
    total_pages = get_total_pages(BUSINESS_SLUG)

    # Assert
    assert total_pages == 0
    mock_make_request.assert_called_once()
    mock_logger.warning.assert_called_once_with(f"Business not found: {BUSINESS_SLUG}")


@patch('hellopeter_cli.hellopeter_scraper.make_api_request')
def test_fetch_business_stats_success(mock_make_request):
    """Test fetching business stats successfully."""
    # Arrange
    mock_make_request.return_value = SAMPLE_STATS_RESPONSE

    # Act
    business_data, stats_data = fetch_business_stats(BUSINESS_SLUG)

    # Assert
    assert stats_data == SAMPLE_STATS_RESPONSE
    assert business_data is not None
    assert business_data["slug"] == BUSINESS_SLUG
    assert business_data["name"] == SAMPLE_STATS_RESPONSE["monthlyStats"]["businessName"]
    assert business_data["industry_name"] == SAMPLE_STATS_RESPONSE["monthlyStats"]["industryName"]
    assert business_data["industry_slug"] == SAMPLE_STATS_RESPONSE["monthlyStats"]["industrySlug"]
    mock_make_request.assert_called_once_with(BASE_STATS_URL)


@patch('hellopeter_cli.hellopeter_scraper.make_api_request')
@patch('hellopeter_cli.hellopeter_scraper.logger')
def test_fetch_business_stats_not_found(mock_logger, mock_make_request):
    """Test fetching business stats when business is not found (404)."""
    # Arrange
    mock_response = requests.Response()
    mock_response.status_code = 404
    mock_make_request.side_effect = requests.exceptions.HTTPError(response=mock_response)

    # Act
    business_data, stats_data = fetch_business_stats(BUSINESS_SLUG)

    # Assert
    assert business_data is None
    assert stats_data is None
    mock_make_request.assert_called_once_with(BASE_STATS_URL)
    mock_logger.warning.assert_called_once_with(f"Business not found: {BUSINESS_SLUG}")


@patch('hellopeter_cli.hellopeter_scraper.get_total_pages', return_value=2)
@patch('hellopeter_cli.hellopeter_scraper.make_api_request')
@patch('tqdm.tqdm') # Mock tqdm to avoid progress bar output
def test_fetch_reviews_for_business_all_pages(mock_tqdm, mock_make_request, mock_get_total):
    """Test fetching all pages of reviews for a business."""
    # Arrange
    # Define side effects for make_api_request for page 1 and page 2
    mock_make_request.side_effect = [SAMPLE_REVIEWS_PAGE_1, SAMPLE_REVIEWS_PAGE_2]
    expected_url = BASE_REVIEWS_URL
    expected_calls_args = [
        ( (expected_url, {"page": 1, "count": 10}), {} ), # Args tuple, kwargs dict
        ( (expected_url, {"page": 2, "count": 10}), {} )
    ]

    # Act
    business_data, all_reviews = fetch_reviews_for_business(BUSINESS_SLUG)

    # Assert
    mock_get_total.assert_called_once_with(BUSINESS_SLUG)
    assert mock_make_request.call_count == 2
    # Check calls explicitly
    assert mock_make_request.call_args_list == expected_calls_args

    assert business_data is not None
    assert business_data["slug"] == BUSINESS_SLUG
    assert business_data["name"] == "Scraper Biz" # From first review
    assert business_data["industry_name"] == "Scraping"
    assert business_data["industry_slug"] == "scraping"

    assert len(all_reviews) == 4 # 2 from page 1, 2 from page 2
    assert all_reviews[0]["id"] == 201
    assert all_reviews[1]["id"] == 202
    assert all_reviews[2]["id"] == 203
    assert all_reviews[3]["id"] == 204


@patch('hellopeter_cli.hellopeter_scraper.make_api_request')
@patch('tqdm.tqdm')
def test_fetch_reviews_for_business_page_range(mock_tqdm, mock_make_request):
    """Test fetching a specific range of pages."""
    # Arrange
    # We only expect page 2 to be called in this case
    mock_make_request.return_value = SAMPLE_REVIEWS_PAGE_2
    expected_url = BASE_REVIEWS_URL
    expected_args = (expected_url, {"page": 2, "count": 10})
    expected_kwargs = {}

    # Act
    # Note: get_total_pages is NOT called when end_page is specified
    business_data, all_reviews = fetch_reviews_for_business(BUSINESS_SLUG, start_page=2, end_page=2)

    # Assert
    assert mock_make_request.call_count == 1
    args, kwargs = mock_make_request.call_args
    assert args == expected_args
    assert kwargs == expected_kwargs

    assert business_data is not None # Gets data from the first page fetched (page 2)
    assert len(all_reviews) == 2
    assert all_reviews[0]["id"] == 203


@patch('hellopeter_cli.hellopeter_scraper.get_total_pages', return_value=2)
@patch('hellopeter_cli.hellopeter_scraper.make_api_request')
@patch('hellopeter_cli.hellopeter_scraper.logger')
@patch('tqdm.tqdm')
def test_fetch_reviews_for_business_stop_early(mock_tqdm, mock_logger, mock_make_request, mock_get_total):
    """Test that fetching stops early if existing reviews are found."""
    # Arrange
    existing_ids = {203, 204} # Pretend reviews from page 2 already exist
    # API will return page 1 (new reviews), then page 2 (existing reviews)
    mock_make_request.side_effect = [SAMPLE_REVIEWS_PAGE_1, SAMPLE_REVIEWS_PAGE_2]
    expected_url = BASE_REVIEWS_URL
    expected_calls_args = [
        ( (expected_url, {"page": 1, "count": 10}), {} ),
        ( (expected_url, {"page": 2, "count": 10}), {} )
    ]

    # Act
    business_data, all_reviews = fetch_reviews_for_business(BUSINESS_SLUG, existing_review_ids=existing_ids)

    # Assert
    mock_get_total.assert_called_once_with(BUSINESS_SLUG)
    # Crucially, only two API calls should be made (page 1 and page 2)
    # The loop should break after processing page 2 because its reviews exist
    assert mock_make_request.call_count == 2
    # Check calls explicitly
    assert mock_make_request.call_args_list == expected_calls_args

    # Only reviews from page 1 should be in the results
    assert len(all_reviews) == 2
    assert all_reviews[0]["id"] == 201
    assert all_reviews[1]["id"] == 202

    # Check that the informational log message was generated
    mock_logger.info.assert_any_call("Reached existing reviews at page 2, stopping fetch")


# Test save_raw_data
@patch("builtins.open", new_callable=mock_open) # Use mock_open utility
@patch('os.makedirs')
@patch('json.dump')
@patch('hellopeter_cli.hellopeter_scraper.logger')
def test_save_raw_data(mock_logger, mock_json_dump, mock_makedirs, mock_open_instance):
    """Test saving raw data to a JSON file."""
    # Arrange
    test_data = {"key": "value"}
    data_type = "test_type"
    output_dir_arg = "custom_output"

    # Act
    filename = save_raw_data(BUSINESS_SLUG, data_type, test_data, output_dir=output_dir_arg)

    # Assert
    mock_makedirs.assert_called_once_with(output_dir_arg, exist_ok=True)
    # Check filename structure (timestamp makes exact match hard, so check components)
    assert filename.startswith(f"{output_dir_arg}/{data_type}_{BUSINESS_SLUG}_")
    assert filename.endswith(".json")

    # Check open was called correctly
    mock_open_instance.assert_called_once_with(filename, 'w', encoding='utf-8')
    # Check that dump was called with the handle provided by mock_open
    mock_json_dump.assert_called_once_with(test_data, mock_open_instance(), ensure_ascii=False, indent=2)
    mock_logger.info.assert_called_once_with(f"Raw data saved to {filename}") 