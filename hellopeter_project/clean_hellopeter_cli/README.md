# HelloPeter CLI

A command-line tool for extracting reviews and statistics from the HelloPeter platform.

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
- python-dotenv: Included for potential future use with environment variables

These dependencies are listed in the `requirements.txt` file and will be automatically installed when you install the package.

## Configuration

The tool uses a configuration file (`config.py`) with the following settings:

- API endpoints for HelloPeter
- Rate limiting settings (delay between requests, retries, backoff factor)
- Database path (automatically set to `~/.hellopeter_cli/hellopeter_reviews.db`)
- Default output directory

Currently, all configuration is done through the command-line arguments. The tool does not use environment variables, but the python-dotenv package is included for potential future use.

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

### Saving Raw API Responses

To save the raw API responses:

```bash
hellopeter-cli fetch --businesses bank-zero-mutual-bank --save-raw
```

### Avoiding Duplicate Reviews

When using the database output format, the tool automatically checks for existing reviews and only fetches new ones. The tool is optimized to stop fetching as soon as it encounters reviews that already exist in the database, making it efficient even for businesses with thousands of reviews.

To force fetching all reviews, even if they already exist in the database:

```bash
hellopeter-cli fetch --businesses bank-zero-mutual-bank --output-format db --force-refresh
```

### Logging

You can specify a log file to capture all log messages:

```bash
hellopeter-cli fetch --businesses bank-zero-mutual-bank --log-file hellopeter.log
```

### Database Operations

The tool automatically creates and initializes a SQLite database in your home directory at `~/.hellopeter_cli/hellopeter_reviews.db` when you use the `db` output format.

To reset the database:

```bash
hellopeter-cli reset
```

## Output

### CSV Output

When using the CSV output format, the following files will be created:
- `businesses.csv`: Information about the businesses
- `reviews_<business-slug>.csv`: Reviews for each business
- `business_stats_<business-slug>.csv`: Statistics for each business

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

## Scheduling

For automated data collection, you can schedule the tool to run periodically using a scheduler like cron (Linux/macOS) or Task Scheduler (Windows).

Example cron job to run daily at 2 AM:
```
0 2 * * * /path/to/hellopeter-cli fetch --businesses bank-zero-mutual-bank --output-format db
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 