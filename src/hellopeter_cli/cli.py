#!/usr/bin/env python3
"""
Hellopeter-CLI - A command-line tool for extracting reviews and statistics from Hellopeter.

This tool allows you to extract reviews and business statistics from the Hellopeter platform
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
from .hellopeter_scraper import fetch_business_stats, fetch_reviews_for_business
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
    """Save stats and reviews data to CSV files, including business details in each file.
    
    No separate business CSV is created; business details are added as columns.
    """
    os.makedirs(output_dir, exist_ok=True)
    something_saved = False # Track if any file was actually saved
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Prepare business details to add as columns (use defaults if business_data is missing)
    biz_details = {
        'business_slug': business_slug, 
        'business_name': business_data.get('name', business_slug) if business_data else business_slug,
        'business_industry_name': business_data.get('industry_name') if business_data else None,
        'business_industry_slug': business_data.get('industry_slug') if business_data else None
    }

    # --- Remove separate business file saving --- 
    # if business_data:
    #     business_file = os.path.join(output_dir, f"business_{business_slug}_{timestamp}.csv")
    #     business_df = pd.DataFrame([business_data] if isinstance(business_data, dict) else business_data)
    #     business_df.to_csv(business_file, index=False, encoding='utf-8')
    #     logger.info(f"Business data saved to {business_file}")
    #     something_saved = True 
    
    # Save reviews (with added business columns)
    if reviews:
        reviews_file = os.path.join(output_dir, f"reviews_{business_slug}_{timestamp}.csv")
        reviews_df = pd.DataFrame(reviews)
        # Add business columns
        for col_name, value in biz_details.items():
            reviews_df[col_name] = value
        # Reorder columns to put business info first (optional)
        business_cols = list(biz_details.keys())
        other_cols = [col for col in reviews_df.columns if col not in business_cols]
        reviews_df = reviews_df[business_cols + other_cols]
        
        reviews_df.to_csv(reviews_file, index=False, encoding='utf-8')
        logger.info(f"Reviews (with business details) saved to {reviews_file}")
        something_saved = True
    
    # Save stats data (with added business columns)
    if stats_data:
        stats_file = os.path.join(output_dir, f"stats_{business_slug}_{timestamp}.csv")
        
        # Extract specific fields like the database does
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

        # Convert extracted stats to a DataFrame
        stats_df = pd.DataFrame([extracted_stats] if isinstance(extracted_stats, dict) else extracted_stats)
        
        # Add business columns
        for col_name, value in biz_details.items():
            stats_df[col_name] = value
         # Reorder columns to put business info first (optional)
        business_cols = list(biz_details.keys())
        other_cols = [col for col in stats_df.columns if col not in business_cols]
        stats_df = stats_df[business_cols + other_cols]

        stats_df.to_csv(stats_file, index=False, encoding='utf-8')
        logger.info(f"Business stats (structured, with business details) saved to {stats_file}")
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

    total_reviews_fetched = 0
    slugs_processed = 0
    slugs_skipped = 0

    for business_slug in businesses:
        logger.info(f"Processing slug: {business_slug}")

        # Reset data variables for this slug
        business_data_to_save = None
        stats_data_to_save = None
        reviews_to_save = None
        fetch_successful = False # Track if any part of the fetch succeeded

        try:
            # --- Fetch Business Stats (if requested) --- 
            if not args.reviews_only:
                logger.info(f"Attempting to fetch business stats for {business_slug}...")
                temp_business_data, temp_stats_data = fetch_business_stats(business_slug)

                # === Check for Stats Fetch Failure ===
                if temp_business_data is None and temp_stats_data is None:
                    logger.warning(f"Stats fetch failed for {business_slug} (e.g., 404 or API error). Will proceed to check for reviews.")
                    # Do not continue yet, reviews might still work
                else:
                    fetch_successful = True # At least stats part worked
                    business_data_to_save = temp_business_data # Store potentially valid data
                    stats_data_to_save = temp_stats_data

                    # Log success or partial success
                    if business_data_to_save:
                        logger.info(f"Successfully fetched business details for {business_data_to_save.get('name', business_slug)}.")
                    if stats_data_to_save:
                         logger.info(f"Successfully fetched stats data for {business_slug}.")
                    elif business_data_to_save:
                         logger.warning(f"Fetched business details but no stats data for {business_slug}.")

            # --- Fetch Reviews (if requested) --- 
            if not args.stats_only:
                logger.info(f"Attempting to fetch reviews for {business_slug}...")
                existing_review_ids = None
                if args.output_format == "db" and not args.force_refresh:
                    session = Session()
                    try:
                        existing_review_ids = get_existing_review_ids(session, business_slug)
                        if existing_review_ids:
                            logger.info(f"Found {len(existing_review_ids)} existing reviews for {business_slug} in the database, will fetch only newer ones.")
                    finally:
                        session.close()

                temp_business_data_reviews, temp_reviews = fetch_reviews_for_business(
                    business_slug,
                    start_page=args.start_page,
                    end_page=args.end_page,
                    existing_review_ids=existing_review_ids
                )

                # === Check for Reviews Fetch Failure ===
                if temp_business_data_reviews is None and not temp_reviews:
                     # Log failure only if stats also failed or weren't requested
                     if not fetch_successful:
                          logger.warning(f"Reviews fetch also failed for {business_slug}. No data could be retrieved.")
                     else:
                          logger.info(f"No new reviews found or fetched for {business_slug}.")
                     # Do not set reviews_to_save if temp_reviews is empty/None
                else:
                    fetch_successful = True # Reviews part worked or returned business data
                    reviews_to_save = temp_reviews # Store valid reviews (can be empty list)

                    # Update business_data if reviews fetch provided it and we didn't get it from stats
                    if temp_business_data_reviews and business_data_to_save is None:
                        business_data_to_save = temp_business_data_reviews
                        logger.info(f"Business details obtained from reviews fetch for {business_data_to_save.get('name', business_slug)}.")

                    # Log review fetch results
                    if reviews_to_save:
                        current_biz_name = business_data_to_save.get('name', business_slug) if business_data_to_save else business_slug
                        logger.info(f"Successfully fetched {len(reviews_to_save)} reviews for {current_biz_name}.")
                        total_reviews_fetched += len(reviews_to_save)
                    elif temp_business_data_reviews:
                        # Got business data but no reviews
                        logger.info(f"No new reviews found or fetched for {business_slug}, but business details were confirmed.")

            # --- Post-Fetch Processing --- 

            # If after all attempts, no fetch was successful, skip this slug entirely
            if not fetch_successful:
                logger.error(f"Failed to fetch any data (stats or reviews) for slug '{business_slug}'. Skipping.")
                slugs_skipped += 1
                continue # Go to the next business slug

            # Create Placeholder Business Data ONLY if needed for saving associated stats/reviews
            if business_data_to_save is None and (stats_data_to_save is not None or (reviews_to_save is not None and len(reviews_to_save) > 0)):
                 logger.warning(f"No valid business details found for {business_slug}, creating minimal placeholder entry because associated stats/reviews exist.")
                 business_data_to_save = {
                     "slug": business_slug,
                     "name": business_slug, # Use slug as name placeholder
                     "industry_name": None,
                     "industry_slug": None
                 }

            # --- Save Data (Single Call per Slug) --- 
            # Only proceed if we have *something* concrete to save (business details, stats, or non-empty reviews)
            should_save = (business_data_to_save is not None or 
                           stats_data_to_save is not None or 
                           (reviews_to_save is not None)) # Check if list exists, even if empty for stats saving

            if should_save:
                logger.info(f"Proceeding to save data for slug {business_slug} in {args.output_format} format.")
                # Use the determined business_data (could be real or placeholder)
                final_business_data = business_data_to_save 
                
                if args.output_format == "db":
                    # Call original save_to_database
                    save_success = save_to_database(
                        final_business_data, 
                        reviews=reviews_to_save, # Pass the list
                        stats_data=stats_data_to_save
                    )
                    if not save_success:
                         logger.error(f"Database save operation failed for slug {business_slug}.")

                elif args.output_format == "csv":
                    # Pass only non-None data to avoid creating empty files unless necessary
                    save_to_csv(args.output_dir, business_slug, 
                                business_data=final_business_data if final_business_data else None, 
                                reviews=reviews_to_save if reviews_to_save else None, 
                                stats_data=stats_data_to_save if stats_data_to_save else None)
                elif args.output_format == "json":
                     # Pass only non-None data
                    save_to_json(args.output_dir, business_slug, 
                                 business_data=final_business_data if final_business_data else None, 
                                 reviews=reviews_to_save if reviews_to_save else None, 
                                 stats_data=stats_data_to_save if stats_data_to_save else None)
                slugs_processed += 1
            else:
                # This case should now be rare due to the 'fetch_successful' check earlier,
                # but acts as a safeguard.
                logger.info(f"No data fetched or requiring saving for slug {business_slug}.")
            slugs_skipped += 1

        except Exception as e:
            logger.exception(f"Unexpected error processing {business_slug}: {e}", exc_info=True) # Log full traceback
            slugs_skipped += 1
            # Continue to the next business slug

    logger.info(f"--- Fetch Summary ---")
    logger.info(f"Total slugs processed and saved: {slugs_processed}")
    logger.info(f"Total slugs skipped (due to fetch errors or no data): {slugs_skipped}")
    logger.info(f"Total reviews fetched across all processed slugs: {total_reviews_fetched}")
    logger.info(f"---------------------")
    return 0 # Return 0 for success, even if some slugs failed


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
    
    # Reset command
    reset_parser = subparsers.add_parser(
        "reset", 
        help="Reset the database",
        description="Drops all tables (businesses, reviews, business_stats) from the database and recreates them empty. Use with caution as this deletes all stored data."
    )
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