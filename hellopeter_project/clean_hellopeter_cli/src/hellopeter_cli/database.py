"""
Database module for storing HelloPeter reviews.
"""
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
# from sqlalchemy.ext.declarative import declarative_base # Deprecated
from sqlalchemy.orm import sessionmaker, relationship, declarative_base # Updated import

from . import config

# Set up logging
logger = logging.getLogger(__name__)

# Create SQLAlchemy base
Base = declarative_base()

# Create SQLAlchemy engine and session
engine = create_engine(config.DB_CONNECTION_STRING)
Session = sessionmaker(bind=engine)


class Business(Base):
    """Business model for storing business information."""
    __tablename__ = 'businesses'

    id = Column(Integer, primary_key=True)
    slug = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    industry_name = Column(String(255))
    industry_slug = Column(String(255))
    
    # Relationships
    reviews = relationship("Review", back_populates="business")
    stats = relationship("BusinessStats", back_populates="business", uselist=False)
    
    def __repr__(self):
        return f"<Business(name='{self.name}', slug='{self.slug}')>"


class Review(Base):
    """Review model for storing review information."""
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, unique=True, nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
    user_id = Column(String(255))
    created_at = Column(DateTime)
    author_display_name = Column(String(255))
    author = Column(String(255))
    author_id = Column(String(255))
    review_title = Column(String(512))
    review_rating = Column(Integer)
    review_content = Column(Text)
    permalink = Column(String(512))
    replied = Column(Boolean, default=False)
    nps_rating = Column(Integer, nullable=True)
    source = Column(String(50))
    is_reported = Column(Boolean, default=False)
    author_created_date = Column(DateTime, nullable=True)
    author_total_reviews_count = Column(Integer, nullable=True)
    
    # Relationships
    business = relationship("Business", back_populates="reviews")
    
    def __repr__(self):
        return f"<Review(id={self.review_id}, title='{self.review_title}', rating={self.review_rating})>"


class BusinessStats(Base):
    """Business stats model for storing statistics from the business-stats endpoint."""
    __tablename__ = 'business_stats'

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('businesses.id'), unique=True, nullable=False)
    total_reviews = Column(Integer)
    average_rating = Column(Float)
    trust_index = Column(Float)
    rating_1_count = Column(Integer)
    rating_2_count = Column(Integer)
    rating_3_count = Column(Integer)
    rating_4_count = Column(Integer)
    rating_5_count = Column(Integer)
    industry_id = Column(Integer, nullable=True)
    industry_ranking = Column(Integer, nullable=True)
    review_count_total = Column(Integer, nullable=True)
    avg_response_time = Column(Float, nullable=True)
    response_rate = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=datetime.now)
    
    # Relationships
    business = relationship("Business", back_populates="stats")
    
    def __repr__(self):
        return f"<BusinessStats(business_id={self.business_id}, total_reviews={self.total_reviews}, average_rating={self.average_rating})>"


def init_db():
    """Initialize the database by creating all tables."""
    # Create tables
    Base.metadata.create_all(engine)
    logger.info(f"Database initialized successfully at {config.DEFAULT_DB_PATH}")
    return engine, Session


def get_or_create_business(session, slug, name, industry_name=None, industry_slug=None):
    """Get an existing business or create a new one if it doesn't exist."""
    business = session.query(Business).filter_by(slug=slug).first()
    if not business:
        business = Business(
            slug=slug,
            name=name,
            industry_name=industry_name,
            industry_slug=industry_slug
        )
        session.add(business)
        session.commit()
        logger.info(f"Created new business: {name} ({slug})")
    return business


def store_review(session, review_data, business_id):
    """Store a review in the database."""
    # Check if review already exists
    existing_review = session.query(Review).filter_by(review_id=review_data['id']).first()
    if existing_review:
        logger.debug(f"Review {review_data['id']} already exists, skipping.")
        return existing_review
    
    # Parse datetime strings
    created_at = datetime.strptime(review_data['created_at'], "%Y-%m-%d %H:%M:%S") if review_data.get('created_at') else None
    author_created_date = datetime.strptime(review_data['author_created_date'], "%Y-%m-%d") if review_data.get('author_created_date') else None
    
    # Create new review
    review = Review(
        review_id=review_data['id'],
        business_id=business_id,
        user_id=review_data.get('user_id'),
        created_at=created_at,
        author_display_name=review_data.get('authorDisplayName'),
        author=review_data.get('author'),
        author_id=review_data.get('author_id'),
        review_title=review_data.get('review_title'),
        review_rating=review_data.get('review_rating'),
        review_content=review_data.get('review_content'),
        permalink=review_data.get('permalink'),
        replied=review_data.get('replied', 0) == 1,
        nps_rating=review_data.get('nps_rating'),
        source=review_data.get('source'),
        is_reported=review_data.get('is_reported', False),
        author_created_date=author_created_date,
        author_total_reviews_count=review_data.get('author_total_reviews_count')
    )
    
    session.add(review)
    session.commit()
    logger.debug(f"Stored review {review.review_id}: {review.review_title}")
    
    return review


def store_business_stats(session, business_id, stats_data):
    """Store business statistics in the database."""
    # Check if stats already exist for this business
    existing_stats = session.query(BusinessStats).filter_by(business_id=business_id).first()
    
    # Extract monthly stats
    monthly_stats = stats_data.get('monthlyStats', {})
    
    # Extract rating distribution from reviewRatings
    rating_1_count = 0
    rating_2_count = 0
    rating_3_count = 0
    rating_4_count = 0
    rating_5_count = 0
    
    # Extract from the reviewRatings structure
    review_ratings = stats_data.get('reviewRatings', {})
    rows = review_ratings.get('rows', [])
    
    for row in rows:
        if len(row) >= 2:
            rating_label = row[0]
            rating_count = row[1]
            
            if "1 Star" in rating_label:
                rating_1_count = rating_count
            elif "2 Stars" in rating_label:
                rating_2_count = rating_count
            elif "3 Stars" in rating_label:
                rating_3_count = rating_count
            elif "4 Stars" in rating_label:
                rating_4_count = rating_count
            elif "5 Stars" in rating_label:
                rating_5_count = rating_count
    
    # Extract average rating
    average_rating = 0.0
    if stats_data.get('reviewAverage'):
        try:
            average_rating = float(stats_data.get('reviewAverage', '0.0'))
        except (ValueError, TypeError):
            logger.warning(f"Could not convert reviewAverage to float: {stats_data.get('reviewAverage')}")
    
    # Create or update stats
    if existing_stats:
        # Update existing stats
        existing_stats.total_reviews = stats_data.get('totalReviews', 0)
        existing_stats.average_rating = average_rating
        existing_stats.trust_index = monthly_stats.get('trustIndex', 0.0)
        existing_stats.rating_1_count = rating_1_count
        existing_stats.rating_2_count = rating_2_count
        existing_stats.rating_3_count = rating_3_count
        existing_stats.rating_4_count = rating_4_count
        existing_stats.rating_5_count = rating_5_count
        existing_stats.industry_id = monthly_stats.get('industryId')
        existing_stats.industry_ranking = monthly_stats.get('industryRanking')
        existing_stats.review_count_total = monthly_stats.get('reviewCountTotal')
        existing_stats.avg_response_time = stats_data.get('avgResponseTime')
        existing_stats.response_rate = stats_data.get('responseRate')
        existing_stats.last_updated = datetime.now()
        
        logger.debug(f"Updated business stats for business_id={business_id}")
        stats = existing_stats
    else:
        # Create new stats
        stats = BusinessStats(
            business_id=business_id,
            total_reviews=stats_data.get('totalReviews', 0),
            average_rating=average_rating,
            trust_index=monthly_stats.get('trustIndex', 0.0),
            rating_1_count=rating_1_count,
            rating_2_count=rating_2_count,
            rating_3_count=rating_3_count,
            rating_4_count=rating_4_count,
            rating_5_count=rating_5_count,
            industry_id=monthly_stats.get('industryId'),
            industry_ranking=monthly_stats.get('industryRanking'),
            review_count_total=monthly_stats.get('reviewCountTotal'),
            avg_response_time=stats_data.get('avgResponseTime'),
            response_rate=stats_data.get('responseRate')
        )
        
        session.add(stats)
        logger.debug(f"Stored business stats for business_id={business_id}")
    
    session.commit()
    return stats 


def get_latest_review_date(session, business_slug):
    """Get the date of the most recent review for a business.
    
    Args:
        session: SQLAlchemy session
        business_slug: Business slug to check
        
    Returns:
        datetime: Date of the most recent review, or None if no reviews exist
    """
    business = session.query(Business).filter_by(slug=business_slug).first()
    if not business:
        return None
        
    latest_review = session.query(Review).filter_by(business_id=business.id).order_by(Review.created_at.desc()).first()
    if not latest_review:
        return None
        
    return latest_review.created_at


def get_existing_review_ids(session, business_slug):
    """Get a set of existing review IDs for a business.
    
    Args:
        session: SQLAlchemy session
        business_slug: Business slug to check
        
    Returns:
        set: Set of review IDs already in the database
    """
    business = session.query(Business).filter_by(slug=business_slug).first()
    if not business:
        return set()
        
    review_ids = session.query(Review.review_id).filter_by(business_id=business.id).all()
    return set(r[0] for r in review_ids) 