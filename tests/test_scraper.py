import pytest
import requests
import requests_mock
import time
import json
import os
from unittest.mock import patch, call, Mock, mock_open # Import mock_open
import responses

# Adjust import path based on structure
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from hellopeter_cli import config # Need config for URLs and constants
from hellopeter_cli.hellopeter_scraper import (
    make_api_request,
    get_total_pages,
    fetch_business_stats,
    fetch_reviews_for_business
)

# Mock config for tests
config.MAX_RETRIES = 1
config.BACKOFF_FACTOR = 0.1
config.REQUEST_DELAY = 0

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
def test_fetch_reviews_for_business_filter_existing(mock_tqdm, mock_logger, mock_make_request, mock_get_total):
    """Test that fetching continues but filters out existing reviews."""
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
    # It should fetch BOTH pages
    assert mock_make_request.call_count == 2
    # Check calls explicitly
    assert mock_make_request.call_args_list == expected_calls_args

    # Only NEW reviews (from page 1) should be in the final results
    assert len(all_reviews) == 2
    assert all_reviews[0]["id"] == 201
    assert all_reviews[1]["id"] == 202

    # Check that the specific "stopping fetch" INFO message was NOT generated
    stop_call = call("Reached existing reviews at page 2, stopping fetch")
    found_stop_call = False
    for call_item in mock_logger.info.call_args_list:
        if call_item == stop_call:
            found_stop_call = True
            break
    assert not found_stop_call, "The 'stopping fetch' log message should not have been called."
    
    # Check that the DEBUG message about existing reviews WAS generated
    mock_logger.debug.assert_any_call("Page 2: All reviews on this page already existed in the database.")


# --- REMOVE TEST FUNCTION for save_raw_data ---
# @patch("os.makedirs")
# @patch("builtins.open", new_callable=mock_open)
# @patch("hellopeter_cli.hellopeter_scraper.datetime")
# def test_save_raw_data(mock_dt, mock_open_func, mock_makedirs, tmp_path):
#     """Test saving raw data to a file."""
#     # Arrange
#     mock_now = MagicMock()
#     mock_now.strftime.return_value = "20240101_120000"
#     mock_dt.now.return_value = mock_now
#     
#     business_slug = "test-biz"
#     data_type = "reviews"
#     data = [{"id": 1, "text": "Great!"}, {"id": 2, "text": "Okay"}]
#     output_dir_arg = str(tmp_path / "raw_test")
#     expected_filename = os.path.join(output_dir_arg, f"{data_type}_{business_slug}_20240101_120000.json")
#     
#     # Act
#     filename = save_raw_data(business_slug, data_type, data, output_dir=output_dir_arg)
#     
#     # Assert
#     mock_makedirs.assert_called_once_with(output_dir_arg, exist_ok=True)
#     mock_open_func.assert_called_once_with(expected_filename, 'w', encoding='utf-8')
#     handle = mock_open_func()
#     # Check if json.dump was called correctly (it writes to the handle)
#     # We need to check the arguments passed to the write method of the handle
#     # json.dump internally calls handle.write
#     # Check the first call to write (usually where json.dump writes)
#     # Note: This is a bit indirect, checking the mock handle's write calls
#     # It might be better to mock json.dump if possible, but patching builtins.open is common
#     
#     # A simple check: was write called?
#     handle.write.assert_called()
#     # A more specific check (might be brittle depending on json.dump formatting):
#     # expected_json_string = json.dumps(data, ensure_ascii=False, indent=2)
#     # handle.write.assert_any_call(expected_json_string) # Use assert_any_call if multiple writes occur
#     
#     assert filename == expected_filename
# --- END REMOVE TEST FUNCTION --- 

# ... (keep code after the test_save_raw_data function) ... 