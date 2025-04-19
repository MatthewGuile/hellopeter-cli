"""
Export data from the database to CSV or JSON files.
"""
import os
import pandas as pd
from sqlalchemy import create_engine, text

from . import config
from .database import engine

def export_businesses(output_dir=None):
    """Export businesses to a CSV file."""
    output_dir = output_dir or config.DEFAULT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a connection to the database
    with engine.connect() as conn:
        # Query businesses
        query = text("SELECT * FROM businesses")
        df = pd.read_sql(query, conn)
        
        # Save to CSV
        output_file = os.path.join(output_dir, "businesses.csv")
        df.to_csv(output_file, index=False)
        
        return output_file


def export_reviews(business_slug=None, output_dir=None):
    """Export reviews to a CSV file."""
    output_dir = output_dir or config.DEFAULT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a connection to the database
    with engine.connect() as conn:
        # Build query
        if business_slug:
            query = text("""
                SELECT r.* FROM reviews r
                JOIN businesses b ON r.business_id = b.id
                WHERE b.slug = :slug
            """)
            df = pd.read_sql(query, conn, params={"slug": business_slug})
            output_file = os.path.join(output_dir, f"reviews_{business_slug}.csv")
        else:
            query = text("SELECT * FROM reviews")
            df = pd.read_sql(query, conn)
            output_file = os.path.join(output_dir, "reviews.csv")
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        
        return output_file


def export_business_stats(business_slug=None, output_dir=None):
    """Export business statistics to a CSV file."""
    output_dir = output_dir or config.DEFAULT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a connection to the database
    with engine.connect() as conn:
        # Build query
        if business_slug:
            query = text("""
                SELECT bs.* FROM business_stats bs
                JOIN businesses b ON bs.business_id = b.id
                WHERE b.slug = :slug
            """)
            df = pd.read_sql(query, conn, params={"slug": business_slug})
            output_file = os.path.join(output_dir, f"business_stats_{business_slug}.csv")
        else:
            query = text("""
                SELECT bs.*, b.name, b.slug FROM business_stats bs
                JOIN businesses b ON bs.business_id = b.id
            """)
            df = pd.read_sql(query, conn)
            output_file = os.path.join(output_dir, "business_stats.csv")
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        
        return output_file 