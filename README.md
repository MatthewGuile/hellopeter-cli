# HelloPeter CLI

A command-line tool for extracting reviews and statistics from the HelloPeter platform.

## IMPORTANT: Terms of Service and Responsible Use

**Disclaimer:** This tool interacts with the HelloPeter website API. Users are solely responsible for ensuring their use of this tool complies with the current HelloPeter Terms of Service (ToS) and any applicable laws or regulations regarding data scraping and API usage.

*   **Review the ToS:** Before using this tool, please review HelloPeter's official Terms of Service.
*   **Use Responsibly:** Avoid making excessive requests in a short period. The default rate limiting settings (delay between requests, retries) are designed to be respectful, but aggressive usage could negatively impact HelloPeter's services and may violate their ToS.
*   **No Guarantees:** APIs can change without notice. This tool may stop working if HelloPeter modifies its API structure or access policies.

The developers of this tool assume no liability for misuse or for any consequences arising from the user's failure to comply with HelloPeter's Terms of Service.

## Overview

This tool allows you to:

1. Extract reviews and business statistics for specified businesses
2. Store the data in a SQLite database or export to CSV/JSON files

The tool is designed to be respectful of rate limits and includes features like exponential backoff for retries and configurable request delays.

## Installation

### From PyPI

```bash
pip install hellopeter-cli
```

### From Source

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd hellopeter-cli
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

## Dependencies

The tool requires the following Python packages:
- requests: For making API requests
- SQLAlchemy: For database operations
- pandas: For data manipulation and CSV export
- tqdm: For progress bars
- backoff: For exponential backoff on API requests

These dependencies are listed in the `requirements.txt` file and will be automatically installed when you install the package.

## Configuration

The tool uses a configuration file (`config.py`) with the following settings:

- API endpoints for HelloPeter
- Rate limiting settings (delay between requests, retries, backoff factor)
- Database path (defaults to `hellopeter_reviews.db` in the directory where the command is run)
- Default output directory (defaults to `output/` in the directory where the command is run)

All configuration is currently done through command-line arguments.

## Usage

The tool provides commands for different operations:

### Fetching Reviews and Statistics

To fetch reviews and statistics for a specific business, you need to know the exact business slug from HelloPeter. The business slug is the part of the URL after "https://www.hellopeter.com/business/reviews/":

```bash
hellopeter-cli fetch --businesses bank-zero-mutual-bank
```

You can also specify multiple businesses:

```bash
hellopeter-cli fetch --businesses bank-zero-mutual-bank capitec-bank
```

By default, this will save the data to CSV files in the `output` directory. You can change the output format using the `--output-format` option:

```bash
hellopeter-cli fetch --businesses bank-zero-mutual-bank --output-format json
```

Available output formats:
- `csv`: Save data to CSV files (default)
- `json`: Save data to JSON files
- `db`: Save data to a SQLite database

### Fetching Only Reviews or Statistics

To fetch only reviews or only statistics:

```bash
hellopeter-cli fetch --businesses bank-zero-mutual-bank --reviews-only
hellopeter-cli fetch --businesses bank-zero-mutual-bank --stats-only
```

### Pagination Control

You can control which pages of reviews to fetch:

```bash
hellopeter-cli fetch --businesses bank-zero-mutual-bank --start-page 1 --end-page 3
```

### Avoiding Duplicate Reviews

When using the database output format (`--output-format db`), the tool normally checks for existing review IDs and only fetches/stores reviews that are not already present in the database. This is efficient for incrementally adding new reviews.

To force fetching all reviews within the specified page range (or all pages if no range is given), even if they already exist in the database, use the `--force-refresh` option:

```bash
hellopeter-cli fetch --businesses your-business-slug --output-format db --force-refresh
```

This is useful if you suspect the initial fetch missed something, but be aware that it is less efficient as it re-fetches reviews that might already be stored.

### Logging

You can specify a log file to capture all log messages:

```bash
hellopeter-cli fetch --businesses bank-zero-mutual-bank --log-file hellopeter.log
```

### Database Operations

The tool automatically creates and initializes a SQLite database named `hellopeter_reviews.db` in the directory where you run the command, if you use the `db` output format.

To reset the database:

```bash
hellopeter-cli reset
```

## Output

### CSV Output

When using the CSV output format, the following files will be created in the output directory:
- `reviews_<business-slug>_<timestamp>.csv`: Reviews for the business. Includes columns for business details (slug, name, industry) repeated on each row.
- `stats_<business-slug>_<timestamp>.csv`: Statistics for the business. Includes columns for business details (slug, name, industry).

Note: A separate `business_...csv` file is *no longer* created.
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
hellopeter-cli fetch --businesses bank-zero-mutual-bank --output-format db --force-refresh
```

The database file is typically named `hellopeter_reviews.db` and located where you run the command.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 