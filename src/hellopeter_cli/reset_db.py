"""
Reset the database by dropping and recreating all tables.
"""
import os
import logging

from . import config
from .database import Base, engine, Session

# Set up logging
logger = logging.getLogger(__name__)

def reset_database():
    """Drop and recreate all tables in the database."""
    # If using SQLite, handle file deletion
    db_path = config.DEFAULT_DB_PATH
    if os.path.exists(db_path):
        logger.info(f"Removing SQLite database file: {db_path}")
        try:
            # Close all connections
            Session.close_all()
            
            # Remove the file
            os.remove(db_path)
            logger.info(f"SQLite database file removed.")
        except Exception as e:
            logger.error(f"Error removing SQLite database file: {e}")
            return False
    
    # Create all tables
    logger.info("Creating all tables...")
    Base.metadata.create_all(engine)
    logger.info("All tables created successfully.")
    
    logger.info("Database reset completed successfully.")
    return True 