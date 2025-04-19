"""
Configuration settings Hellopeter-CLI.
"""
import os
import logging
from pathlib import Path
from datetime import datetime

# API Configuration
BASE_API_URL = "https://api-v6.hellopeter.com/api/consumer/business"
REVIEWS_ENDPOINT = "reviews"
BUSINESS_STATS_BASE_URL = "https://api-v6.hellopeter.com/api/consumer/business-stats"

# Rate limiting settings
REQUEST_DELAY = 1.0  # Delay between API requests in seconds
MAX_RETRIES = 3      # Maximum number of retries for failed requests
BACKOFF_FACTOR = 2   # Exponential backoff factor for retries

# No default target businesses - users must specify via command line
TARGET_BUSINESSES = []

# Database settings
def get_default_db_path():
    """Get the default database path in the current directory."""
    app_dir = Path(".")  # Current directory
    return str(app_dir / "hellopeter_reviews.db")

# SQLite database path
DEFAULT_DB_PATH = get_default_db_path()
DB_CONNECTION_STRING = f"sqlite:///{DEFAULT_DB_PATH}"

# Logging settings
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(os.path.dirname(DEFAULT_DB_PATH), "hellopeter_scraper.log")

# Output directory for exports
def get_default_output_dir():
    """Get the default output directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"hellopeter_output_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

DEFAULT_OUTPUT_DIR = "output" 