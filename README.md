# Hellopeter-CLI

A command-line tool for extracting reviews and statistics from the Hellopeter platform.

## IMPORTANT: Terms of Service and Responsible Use

**Disclaimer:** This tool interacts with the Hellopeter website API. Users are solely responsible for ensuring their use of this tool complies with the current Hellopeter Terms of Service (ToS) and any applicable laws or regulations regarding data scraping and API usage.

*   **Use Responsibly:** Avoid making excessive requests in a short period. The default rate limiting settings (delay between requests, retries) are designed to be respectful, but aggressive usage could negatively impact Hellopeter's services and may violate their ToS.
*   **No Guarantees:** APIs can change without notice. This tool may stop working if Hellopeter modifies its API structure or access policies.

The developers of this tool assume no liability for misuse or for any consequences arising from the user's failure to comply with Hellopeter's Terms of Service.

## Overview

This tool allows you to:

1. Extract reviews and business statistics for specified businesses
2. Store the data in a SQLite database or export to CSV/JSON files

The tool is designed to be respectful of rate limits and includes features like exponential backoff for retries and configurable request delays.

## Installation

If you want to install the package directly from the source code, for example, to get the latest changes or modify the code:

1. Clone this repository:
   ```bash
   git clone https://github.com/MatthewGuile/Hellopeter-CLI
   cd Hellopeter-CLI
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   # Example using venv (Python 3.3+)
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On macOS/Linux
   # source venv/bin/activate
   ```

3. Install the package in editable mode. This installs only the core runtime dependencies:
   ```bash
   pip install -e .
   ```
   (Use `pip install .` for a non-editable install).

**Development / Running Tests:**

If you plan to run the unit tests or contribute to development, you need to install the additional testing dependencies. You can do this using:
```bash
pip install -e .[test]
```
This command installs the core package in editable mode plus the 'test' extras (like pytest, pytest-mock, etc.) defined in `setup.py`.

## Dependencies

The core runtime dependencies (automatically installed via pip or `pip install .`) are:
- `requests`
- `SQLAlchemy`
- `pandas`
- `tqdm`
- `backoff`

These are defined in `setup.py` under `install_requires`.

Development and testing dependencies (like `pytest`, `pytest-mock`, `responses`, `requests-mock`) are defined under `extras_require['test']` in `setup.py` and can be installed as shown in the "Development Setup" section above.

*(Note: Dependencies for installation are managed via `setup.py`. Use the `pip install .` or `pip install -e .` commands for installation, which utilize `setup.py`, rather than directly using `pip install -r requirements.txt` for this package.)*

## Configuration

The tool uses a configuration file (`config.py`) with the following settings:

- API endpoints for Hellopeter
- Rate limiting settings (delay between requests, retries, backoff factor)
- Database path (defaults to `Hellopeter_reviews.db` in the directory where the command is run)
- Default output directory (defaults to `output/` in the directory where the command is run)

All configuration is done through command-line arguments.

## Usage

The tool provides commands for different operations:

### Getting Help

You can get help on the available commands and their options using the `-h` or `--help` flag:

```bash
# General help and list of commands
Hellopeter-cli -h

# Help for the 'fetch' command
Hellopeter-cli fetch -h

# Help for the 'reset' command
Hellopeter-cli reset -h
```

### Fetching Reviews and Statistics

To fetch reviews and statistics for a specific business, you need to know the exact business slug from Hellopeter. A **business slug** is a unique, URL-friendly identifier used by Hellopeter for a specific business (e.g., `bank-zero-mutual-bank`). You can usually find the slug in the address bar of your web browser when viewing the business's review page on the Hellopeter website; it's the part of the URL after `/business/reviews/`.

```bash
Hellopeter-cli fetch --businesses bank-zero-mutual-bank
```

You can also specify multiple businesses:

```bash
Hellopeter-cli fetch --businesses bank-zero-mutual-bank capitec-bank
```

By default, this will save the data to CSV files in the `output` directory. You can change the output format using the `--output-format` option:

```bash
Hellopeter-cli fetch --businesses bank-zero-mutual-bank --output-format json
```

Available output formats:
- `csv`: Save data to CSV files (default)
- `json`: Save data to JSON files
- `db`: Save data to a SQLite database

### Fetching Only Reviews or Statistics

To fetch only reviews or only statistics:

```bash
Hellopeter-cli fetch --businesses bank-zero-mutual-bank --reviews-only
Hellopeter-cli fetch --businesses bank-zero-mutual-bank --stats-only
```

### Pagination Control

You can control which pages of reviews to fetch:

```bash
Hellopeter-cli fetch --businesses bank-zero-mutual-bank --start-page 1 --end-page 3
```

### Avoiding Duplicate Reviews

When using the database output format (`--output-format db`), the tool normally checks for existing review IDs and only fetches/stores reviews that are not already present in the database. This is efficient for incrementally adding new reviews. However, please note that this approach captures reviews as they exist at the time of retrieval. If a review is later edited on the platform, the stored version will not be updated unless `--force-refresh` is used.

To force fetching all reviews within the specified page range (or all pages if no range is given), even if they already exist in the database, use the `--force-refresh` option:

```bash
Hellopeter-cli fetch --businesses your-business-slug --output-format db --force-refresh
```

This is useful if you suspect the initial fetch missed something, but be aware that it is less efficient as it re-fetches reviews that might already be stored.

### Logging

You can specify a log file to capture all log messages:

```bash
Hellopeter-cli fetch --businesses bank-zero-mutual-bank --log-file Hellopeter.log
```

### Database Operations

The tool automatically creates and initializes a SQLite database named `Hellopeter_reviews.db` in the directory where you run the command, if you use the `db` output format.

To reset the database:

```bash
Hellopeter-cli reset
```

## Output

### CSV Output

When using the CSV output format, the following files will be created in the output directory:
- `reviews_<business-slug>_<timestamp>.csv`: Reviews for the business. Includes columns for business details (slug, name, industry) repeated on each row.
- `stats_<business-slug>_<timestamp>.csv`: Statistics for the business. Includes columns for business details (slug, name, industry).

The `<timestamp>` follows the format `YYYYMMDD_HHMMSS`.

### JSON Output

When using the JSON output format, the following files will be created:
- `business_<business-slug>_<timestamp>.json`: Information about the business
- `reviews_<business-slug>_<timestamp>.json`: Reviews for the business
- `stats_<business-slug>_<timestamp>.json`: Statistics for the business

### Database Output

When using the database output format, the data will be stored in a SQLite database with the following tables:
- `businesses`: Information about businesses
- `reviews`: Reviews for businesses
- `business_stats`: Statistics for businesses

The tool automatically checks for existing reviews in the database and only fetches new ones. If you want to force a refresh of all reviews, you can use the `--force-refresh` option:

```bash
Hellopeter-cli fetch --businesses bank-zero-mutual-bank --output-format db --force-refresh
```

The database file is typically named `Hellopeter_reviews.db` and located where you run the command.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 