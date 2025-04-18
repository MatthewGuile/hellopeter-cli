#!/usr/bin/env python3
"""
HelloPeter CLI - A command-line tool for extracting reviews and statistics from HelloPeter.

This tool allows you to extract reviews and business statistics from the HelloPeter platform
and store them in a SQLite database or export them to CSV/JSON files.
"""
import os
import sys
import json
import argparse
import logging
from datetime import datetime
import pandas as pd

from . import config
from .database import init_db, Session, get_or_create_business, store_review, store_business_stats, get_existing_review_ids
from .hellopeter_scraper import fetch_business_stats, fetch_reviews_for_business, save_raw_data
from .export_data import export_businesses, export_reviews, export_business_stats
from .reset_db import reset_database

# Set up logging
logger = logging.getLogger("hellopeter_cli")
logger.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)


def setup_logging(log_file=None):
    """Set up logging configuration."""
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def save_to_database(business_data, reviews=None, stats_data=None):
    """Save data to the database."""
    # Initialize the database if needed
    try:
        init_db()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False
    
    session = Session()
    try:
        # Get or create business
        business = get_or_create_business(
            session,
            business_data["slug"],
            business_data["name"],
            business_data.get("industry_name"),
            business_data.get("industry_slug")
        )
        
        # Store reviews if provided
        if reviews:
            count = 0
            for review_data in reviews:
                store_review(session, review_data, business.id)
                count += 1
            logger.info(f"Saved {count} reviews for {business_data['name']} to database")
        
        # Store business stats if provided
        if stats_data:
            store_business_stats(session, business.id, stats_data)
            logger.info(f"Saved business stats for {business_data['name']} to database")
        
        return True
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def save_to_csv(output_dir, business_slug, business_data=None, reviews=None, stats_data=None):
    """Save data to CSV files, mimicking the database structure for stats."""
    os.makedirs(output_dir, exist_ok=True)
    something_saved = False # Track if any file was actually saved
    
    # Save business data
    if business_data:
        business_file = os.path.join(output_dir, f"business_{business_slug}.csv")
        # Ensure business_data is treated as a single row
        business_df = pd.DataFrame([business_data] if isinstance(business_data, dict) else business_data)
        business_df.to_csv(business_file, index=False, encoding='utf-8')
        logger.info(f"Business data saved to {business_file}")
        something_saved = True
    
    # Save reviews
    if reviews:
        reviews_file = os.path.join(output_dir, f"reviews_{business_slug}.csv")
        reviews_df = pd.DataFrame(reviews)
        reviews_df.to_csv(reviews_file, index=False, encoding='utf-8')
        logger.info(f"Reviews saved to {reviews_file}")
        something_saved = True
    
    # Save stats data - Extract specific fields like the database does
    if stats_data:
        extracted_stats = {}

        # --- Mimic extraction from store_business_stats --- 
        monthly_stats = stats_data.get('monthlyStats', {})
        review_ratings = stats_data.get('reviewRatings', {})
        rows = review_ratings.get('rows', [])

        # Top-level stats
        extracted_stats['total_reviews'] = stats_data.get('totalReviews', 0)
        extracted_stats['avg_response_time'] = stats_data.get('avgResponseTime')
        extracted_stats['response_rate'] = stats_data.get('responseRate')

        # Average rating with conversion
        average_rating = 0.0
        try:
            average_rating = float(stats_data.get('reviewAverage', '0.0'))
        except (ValueError, TypeError):
            logger.warning(f"Could not convert reviewAverage to float for CSV: {stats_data.get('reviewAverage')}")
        extracted_stats['average_rating'] = average_rating

        # Rating counts
        rating_counts = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}
        for row in rows:
            if len(row) >= 2:
                rating_label = str(row[0]) # Ensure label is string
                rating_count = row[1]
                if "1 Star" in rating_label:
                    rating_counts['1'] = rating_count
                elif "2 Stars" in rating_label:
                    rating_counts['2'] = rating_count
                elif "3 Stars" in rating_label:
                    rating_counts['3'] = rating_count
                elif "4 Stars" in rating_label:
                    rating_counts['4'] = rating_count
                elif "5 Stars" in rating_label:
                    rating_counts['5'] = rating_count
        extracted_stats['rating_1_count'] = rating_counts['1']
        extracted_stats['rating_2_count'] = rating_counts['2']
        extracted_stats['rating_3_count'] = rating_counts['3']
        extracted_stats['rating_4_count'] = rating_counts['4']
        extracted_stats['rating_5_count'] = rating_counts['5']

        # Stats from monthlyStats
        extracted_stats['trust_index'] = monthly_stats.get('trustIndex', 0.0)
        extracted_stats['industry_id'] = monthly_stats.get('industryId')
        extracted_stats['industry_ranking'] = monthly_stats.get('industryRanking')
        extracted_stats['review_count_total_monthly'] = monthly_stats.get('reviewCountTotal') # Renamed slightly for clarity vs top-level total

        # --- End mimic --- 

        stats_file = os.path.join(output_dir, f"stats_{business_slug}.csv")
        # Ensure extracted_stats is treated as a single row
        stats_df = pd.DataFrame([extracted_stats] if isinstance(extracted_stats, dict) else extracted_stats)
        stats_df.to_csv(stats_file, index=False, encoding='utf-8')
        logger.info(f"Business stats (structured) saved to {stats_file}")
        something_saved = True

    if something_saved:
         logger.info(f"Data exported to CSV files in {output_dir}/")
    # else: # Optional: log if nothing was saved?
    #     logger.info(f"No data provided to save for {business_slug} in CSV format.")


def save_to_json(output_dir, business_slug, business_data=None, reviews=None, stats_data=None):
    """Save data to JSON files."""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if business_data:
        business_file = os.path.join(output_dir, f"business_{business_slug}_{timestamp}.json")
        with open(business_file, 'w') as f:
            json.dump(business_data, f, indent=4)
        logger.info(f"Business data saved to {business_file}")
    
    if reviews:
        reviews_file = os.path.join(output_dir, f"reviews_{business_slug}_{timestamp}.json")
        with open(reviews_file, 'w') as f:
            json.dump(reviews, f, indent=4)
        logger.info(f"Reviews saved to {reviews_file}")
    
    if stats_data:
        stats_file = os.path.join(output_dir, f"stats_{business_slug}_{timestamp}.json")
        with open(stats_file, 'w') as f:
            json.dump(stats_data, f, indent=4)
        logger.info(f"Business stats saved to {stats_file}")


def fetch_command(args):
    """Handle the fetch command."""
    # Initialize database if output format is db
    if args.output_format == "db":
        logger.info("Initializing database...")
        try:
            init_db()
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            logger.error("Falling back to CSV output format.")
            args.output_format = "csv"
    
    # Get list of businesses to fetch
    businesses = args.businesses or config.TARGET_BUSINESSES
    
    if not businesses:
        logger.error("No businesses specified. Please provide at least one business slug.")
        return 1
    
    total_reviews = 0
    
    for business_slug in businesses:
        logger.info(f"Fetching data for business: {business_slug}")
        
        try:
            # Fetch business stats
            if not args.reviews_only:
                logger.info(f"Fetching business stats for {business_slug}...")
                business_data, stats_data = fetch_business_stats(business_slug)
                
                if not business_data:
                    logger.warning(f"No business data found for {business_slug}")
                    # Create minimal business data to allow processing to continue
                    business_data = {
                        "slug": business_slug,
                        "name": business_slug,
                        "industry_name": None,
                        "industry_slug": None
                    }
                
                logger.info(f"Fetched business stats for {business_data['name']}")
                
                # Save raw data if requested
                if args.save_raw:
                    save_raw_data(business_slug, "business_stats", stats_data, args.output_dir)
                
                # Save data based on output format
                if args.output_format == "db":
                    save_to_database(business_data, stats_data=stats_data)
                elif args.output_format == "csv":
                    save_to_csv(args.output_dir, business_slug, business_data=business_data, stats_data=stats_data)
                elif args.output_format == "json":
                    save_to_json(args.output_dir, business_slug, business_data=business_data, stats_data=stats_data)
            
            # Fetch reviews if not stats-only
            if not args.stats_only:
                logger.info(f"Fetching reviews for {business_slug}...")
                
                # Get existing review IDs if using database output
                existing_review_ids = None
                if args.output_format == "db" and not args.force_refresh:
                    session = Session()
                    try:
                        existing_review_ids = get_existing_review_ids(session, business_slug)
                        if existing_review_ids:
                            logger.info(f"Found {len(existing_review_ids)} existing reviews for {business_slug} in the database")
                    finally:
                        session.close()
                
                business_data, reviews = fetch_reviews_for_business(
                    business_slug,
                    start_page=args.start_page,
                    end_page=args.end_page,
                    existing_review_ids=existing_review_ids
                )
                
                if not business_data:
                    logger.warning(f"No business data found for {business_slug}")
                    # Create minimal business data to allow processing to continue
                    business_data = {
                        "slug": business_slug,
                        "name": business_slug,
                        "industry_name": None,
                        "industry_slug": None
                    }
                
                if not reviews:
                    logger.warning(f"No reviews found for {business_slug}")
                else:
                    logger.info(f"Fetched {len(reviews)} reviews for {business_data['name']}")
                    total_reviews += len(reviews)
                
                # Save raw data if requested
                if args.save_raw:
                    save_raw_data(business_slug, "reviews", reviews, args.output_dir)
                
                # Save data based on output format
                if args.output_format == "db":
                    save_to_database(business_data, reviews=reviews)
                elif args.output_format == "csv":
                    save_to_csv(args.output_dir, business_slug, business_data=business_data, reviews=reviews)
                elif args.output_format == "json":
                    save_to_json(args.output_dir, business_slug, business_data=business_data, reviews=reviews)
        
        except Exception as e:
            logger.error(f"Error processing {business_slug}: {e}")
    
    logger.info(f"Fetch completed. Total reviews: {total_reviews}")
    return 0


def reset_command(args):
    """Handle the reset command."""
    logger.info("Resetting database...")
    reset_database()
    logger.info("Database reset completed.")
    
    return 0


def main():
    """Main entry point for the CLI."""
    # Create the main parser
    parser = argparse.ArgumentParser(
        description="HelloPeter CLI - Extract reviews and statistics from HelloPeter",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="You must specify a command: fetch or reset. Use -h with a command for more help."
    )
    
    # Global options
    parser.add_argument("--log-file", 
                       help="Path to a file where logs will be written (in addition to console output)")
    
    # Subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute", required=True)
    
    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch reviews and statistics")
    fetch_parser.add_argument("--businesses", nargs="+", 
                             help="List of business slugs to fetch (e.g., 'bank-zero-mutual-bank')")
    fetch_parser.add_argument("--start-page", type=int, default=1, 
                             help="Page number to start fetching reviews from")
    fetch_parser.add_argument("--end-page", type=int, 
                             help="Page number to stop fetching reviews at (default: fetch all pages)")
    fetch_parser.add_argument("--save-raw", action="store_true", 
                             help="Save raw API responses for debugging or further analysis")
    fetch_parser.add_argument("--stats-only", action="store_true", 
                             help="Only fetch business statistics (no reviews)")
    fetch_parser.add_argument("--reviews-only", action="store_true", 
                             help="Only fetch reviews (no business statistics)")
    fetch_parser.add_argument("--output-format", choices=["db", "csv", "json"], default="csv", 
                             help="Output format: database (db), CSV files, or JSON files")
    fetch_parser.add_argument("--output-dir", default=config.DEFAULT_OUTPUT_DIR, 
                             help="Directory to save output files")
    fetch_parser.add_argument("--force-refresh", action="store_true",
                             help="Force refresh all reviews, even if they already exist in the database")
    fetch_parser.add_argument("--log-file", 
                            help="Path to a file where logs will be written (in addition to console output)")
    
    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset the database")
    reset_parser.add_argument("--log-file", 
                            help="Path to a file where logs will be written (in addition to console output)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_file)
    
    # Execute command
    if args.command == "fetch":
        return fetch_command(args)
    elif args.command == "reset":
        return reset_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 