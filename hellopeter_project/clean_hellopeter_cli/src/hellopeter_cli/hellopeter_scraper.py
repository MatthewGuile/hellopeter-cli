"""
Scraper for the HelloPeter API.
"""
import os
import time
import json
import logging
from datetime import datetime
import requests
import backoff
from tqdm import tqdm

from . import config
from .database import init_db, Session, get_or_create_business, store_review, store_business_stats
# Import version (assuming __init__.py is in the same directory level)
try:
    from . import __version__ as cli_version
except ImportError: # Fallback if import structure is different
    cli_version = "unknown"

# Set up logging
logger = logging.getLogger(__name__)

@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, requests.exceptions.HTTPError),
    max_tries=config.MAX_RETRIES,
    factor=config.BACKOFF_FACTOR
)
def make_api_request(url, params=None):
    """Make a request to the API with exponential backoff for retries."""
    # Construct User-Agent string
    user_agent = f"hellopeter-cli/{cli_version} (https://github.com/MatthewGuile/hellopeter-cli)"
    headers = {'User-Agent': user_agent}

    # Use headers in the request
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()  # Raise an exception for 4XX/5XX responses
    
    # Add a delay to respect rate limits
    time.sleep(config.REQUEST_DELAY)
    
    return response.json()


def get_total_pages(business_slug):
    """Get the total number of pages for a business."""
    url = f"{config.BASE_API_URL}/{business_slug}/{config.REVIEWS_ENDPOINT}"
    params = {"page": 1, "count": 10}
    
    try:
        data = make_api_request(url, params)
        # The API response structure has changed, now using last_page
        total_pages = data.get("last_page", 0)
        return total_pages
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Business not found: {business_slug}")
        else:
            logger.error(f"Error fetching total pages for {business_slug}: {e}")
        return 0


def fetch_business_stats(business_slug):
    """Fetch business statistics from the API."""
    url = f"{config.BUSINESS_STATS_BASE_URL}/{business_slug}"
    
    try:
        stats_data = make_api_request(url)
        
        # Extract business data
        business_data = {
            "slug": business_slug,
            "name": stats_data.get("monthlyStats", {}).get("businessName", business_slug),
            "industry_name": stats_data.get("monthlyStats", {}).get("industryName"),
            "industry_slug": stats_data.get("monthlyStats", {}).get("industrySlug")
        }
        
        return business_data, stats_data
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Business not found: {business_slug}")
        else:
            logger.error(f"Error fetching business stats for {business_slug}: {e}")
        return None, None


def fetch_reviews_for_business(business_slug, start_page=1, end_page=None, existing_review_ids=None):
    """Fetch reviews for a business from the API.
    
    Args:
        business_slug: The business slug to fetch reviews for
        start_page: The page number to start fetching from (default: 1)
        end_page: The page number to stop fetching at (default: fetch all pages)
        existing_review_ids: Set of review IDs that already exist in the database
        
    Returns:
        Tuple of (business_data, reviews)
    """
    url = f"{config.BASE_API_URL}/{business_slug}/{config.REVIEWS_ENDPOINT}"
    
    # Get total pages if end_page is not specified
    if end_page is None:
        total_pages = get_total_pages(business_slug)
        if total_pages == 0:
            return None, []
        end_page = total_pages
    
    # Initialize variables
    all_reviews = []
    business_data = None
    
    # Fetch reviews for each page
    for page in tqdm(range(start_page, end_page + 1), desc=f"Fetching reviews for {business_slug}"):
        params = {"page": page, "count": 10}
        
        try:
            data = make_api_request(url, params)
            
            # Extract business data from the first page
            if page == start_page and not business_data:
                # Check if we have reviews in the response
                reviews_data = data.get("data", [])
                if reviews_data and len(reviews_data) > 0:
                    first_review = reviews_data[0]
                    business_data = {
                        "slug": business_slug,
                        "name": first_review.get("business_name", business_slug),
                        "industry_name": first_review.get("industry_name"),
                        "industry_slug": first_review.get("industry_slug")
                    }
                else:
                    # If no reviews, create minimal business data
                    business_data = {
                        "slug": business_slug,
                        "name": business_slug,
                        "industry_name": None,
                        "industry_slug": None
                    }
            
            # Extract reviews
            reviews_data = data.get("data", [])
            
            # Check if we've reached reviews that already exist in the database
            if existing_review_ids and reviews_data:
                # Check if any reviews on this page already exist
                found_existing = False
                new_reviews = []
                
                for review in reviews_data:
                    if review.get("id") in existing_review_ids:
                        found_existing = True
                    else:
                        new_reviews.append(review)
                
                # Add only new reviews to our collection
                all_reviews.extend(new_reviews)
                
                # If we found existing reviews and didn't add any new ones, we can stop fetching
                if found_existing and not new_reviews:
                    logger.info(f"Reached existing reviews at page {page}, stopping fetch")
                    break
                
                # If we found some existing reviews but also added new ones, continue to the next page
                if found_existing:
                    logger.info(f"Found some existing reviews at page {page}, but also added {len(new_reviews)} new reviews")
            else:
                # No existing reviews to check against, add all reviews
                all_reviews.extend(reviews_data)
            
        except Exception as e:
            logger.error(f"Error fetching reviews for {business_slug} on page {page}: {e}")
            break
    
    return business_data, all_reviews


def save_raw_data(business_slug, data_type, data, output_dir=None):
    """Save raw API responses to JSON files."""
    output_dir = output_dir or "raw_data"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{data_type}_{business_slug}_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Raw data saved to {filename}")
    return filename 