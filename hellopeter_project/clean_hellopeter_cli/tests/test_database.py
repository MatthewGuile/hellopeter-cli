import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from datetime import datetime
import os

# Adjust import path based on structure (assuming tests/ is sibling to src/)
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from hellopeter_cli.database import (
    Base,
    Business,
    Review,
    BusinessStats,
    init_db as actual_init_db, # Avoid name clash with potential test function
    get_or_create_business,
    store_review,
    store_business_stats,
    get_latest_review_date,
    get_existing_review_ids
)
# Import config carefully for DB path if needed, or mock it
# from hellopeter_cli import config


# --- Fixtures ---

@pytest.fixture(scope="function")
def db_session() -> SQLAlchemySession:
    """Fixture for creating an in-memory SQLite database session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine) # Create tables

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine) # Clean up tables after test


# --- Sample Data ---

SAMPLE_BUSINESS_1 = {
    "slug": "test-business-1",
    "name": "Test Business One",
    "industry_name": "Testing",
    "industry_slug": "testing"
}

SAMPLE_BUSINESS_2 = {
    "slug": "test-business-2",
    "name": "Test Business Two"
}

SAMPLE_REVIEW_1 = {
    "id": 101, # This corresponds to review_id in the DB model
    "user_id": "user1",
    "created_at": "2023-10-26 10:00:00",
    "authorDisplayName": "Author One",
    "review_title": "Great Test",
    "review_rating": 5,
    "review_content": "This is a test review.",
    "permalink": "http://example.com/review/101"
}

SAMPLE_REVIEW_2 = {
    "id": 102,
    "user_id": "user2",
    "created_at": "2023-10-27 11:00:00",
    "authorDisplayName": "Author Two",
    "review_title": "Another Test",
    "review_rating": 4,
    "review_content": "Second test review.",
    "permalink": "http://example.com/review/102"
}

SAMPLE_REVIEW_3_SAME_ID = { # Same ID as REVIEW_1 to test duplicate handling
    "id": 101,
    "user_id": "user3",
    "created_at": "2023-10-28 12:00:00",
    "authorDisplayName": "Author Three",
    "review_title": "Duplicate ID Test",
    "review_rating": 1,
    "review_content": "This should not be stored.",
    "permalink": "http://example.com/review/101_dupe"
}


SAMPLE_STATS_1 = {
    "totalReviews": 50,
    "reviewAverage": "4.5",
    "avgResponseTime": 120.5,
    "responseRate": 0.95,
    "monthlyStats": {
        "trustIndex": 8.5,
        "industryId": 99,
        "industryRanking": 1,
        "reviewCountTotal": 15
    },
    "reviewRatings": {
        "rows": [
            ["1 Star", 2],
            ["2 Stars", 3],
            ["3 Stars", 5],
            ["4 Stars", 10],
            ["5 Stars", 30]
        ]
    }
}

SAMPLE_STATS_2_UPDATE = {
    "totalReviews": 60, # Updated
    "reviewAverage": "4.6", # Updated
    "avgResponseTime": 110.0, # Updated
    "responseRate": 0.96, # Updated
    "monthlyStats": {
        "trustIndex": 8.6, # Updated
        "industryId": 99,
        "industryRanking": 1,
        "reviewCountTotal": 25 # Updated
    },
    "reviewRatings": {
        "rows": [ # Updated counts
            ["1 Star", 2],
            ["2 Stars", 3],
            ["3 Stars", 5],
            ["4 Stars", 15], # Updated
            ["5 Stars", 35]  # Updated
        ]
    }
}


# --- Test Functions ---

def test_get_or_create_new_business(db_session: SQLAlchemySession):
    """Test creating a new business when it doesn't exist."""
    # Act
    business = get_or_create_business(
        db_session,
        SAMPLE_BUSINESS_1["slug"],
        SAMPLE_BUSINESS_1["name"],
        SAMPLE_BUSINESS_1.get("industry_name"),
        SAMPLE_BUSINESS_1.get("industry_slug")
    )
    db_session.commit() # Commit needed to make it queryable

    # Assert
    assert business is not None
    assert business.slug == SAMPLE_BUSINESS_1["slug"]
    assert business.name == SAMPLE_BUSINESS_1["name"]
    assert business.industry_name == SAMPLE_BUSINESS_1["industry_name"]
    assert business.id is not None # Should have an ID after commit

    # Verify it's in the DB
    queried_business = db_session.query(Business).filter_by(slug=SAMPLE_BUSINESS_1["slug"]).first()
    assert queried_business is not None
    assert queried_business.name == SAMPLE_BUSINESS_1["name"]


def test_get_or_create_existing_business(db_session: SQLAlchemySession):
    """Test retrieving an existing business."""
    # Arrange: Create the business first
    initial_business = get_or_create_business(
        db_session,
        SAMPLE_BUSINESS_1["slug"],
        SAMPLE_BUSINESS_1["name"]
    )
    db_session.commit()
    initial_id = initial_business.id

    # Act: Call the function again for the same slug
    retrieved_business = get_or_create_business(
        db_session,
        SAMPLE_BUSINESS_1["slug"],
        "DIFFERENT NAME" # Provide different name to ensure it doesn't update
    )

    # Assert
    assert retrieved_business is not None
    assert retrieved_business.id == initial_id # Should be the same object/ID
    assert retrieved_business.name == SAMPLE_BUSINESS_1["name"] # Name should NOT have changed

    # Verify only one record exists
    count = db_session.query(Business).filter_by(slug=SAMPLE_BUSINESS_1["slug"]).count()
    assert count == 1


def test_store_review_new(db_session: SQLAlchemySession):
    """Test storing a completely new review."""
    # Arrange: Create the parent business
    business = get_or_create_business(db_session, SAMPLE_BUSINESS_1["slug"], SAMPLE_BUSINESS_1["name"])
    db_session.commit()

    # Act
    review = store_review(db_session, SAMPLE_REVIEW_1, business.id)
    db_session.commit()

    # Assert
    assert review is not None
    assert review.review_id == SAMPLE_REVIEW_1["id"]
    assert review.business_id == business.id
    assert review.review_title == SAMPLE_REVIEW_1["review_title"]
    assert review.created_at == datetime.strptime(SAMPLE_REVIEW_1["created_at"], "%Y-%m-%d %H:%M:%S")

    # Verify in DB
    queried_review = db_session.query(Review).filter_by(review_id=SAMPLE_REVIEW_1["id"]).first()
    assert queried_review is not None
    assert queried_review.author_display_name == SAMPLE_REVIEW_1["authorDisplayName"]


def test_store_review_duplicate_id(db_session: SQLAlchemySession):
    """Test that storing a review with an existing review_id is skipped."""
    # Arrange: Create business and store the first review
    business = get_or_create_business(db_session, SAMPLE_BUSINESS_1["slug"], SAMPLE_BUSINESS_1["name"])
    initial_review = store_review(db_session, SAMPLE_REVIEW_1, business.id)
    db_session.commit()
    initial_db_id = initial_review.id # The auto-incrementing primary key

    # Act: Attempt to store another review with the same review_id (SAMPLE_REVIEW_1["id"])
    duplicate_review_obj = store_review(db_session, SAMPLE_REVIEW_3_SAME_ID, business.id)
    db_session.commit() # Should have no effect for this review

    # Assert
    assert duplicate_review_obj is not None
    # Crucially, it should return the *existing* review object
    assert duplicate_review_obj.id == initial_db_id
    assert duplicate_review_obj.review_id == SAMPLE_REVIEW_1["id"]
    assert duplicate_review_obj.review_title == SAMPLE_REVIEW_1["review_title"] # Check it's the old title

    # Verify only the original review exists in the DB
    count = db_session.query(Review).filter_by(business_id=business.id).count()
    assert count == 1
    queried_review = db_session.query(Review).filter_by(review_id=SAMPLE_REVIEW_1["id"]).first()
    assert queried_review.review_title == SAMPLE_REVIEW_1["review_title"] # Double-check content wasn't overwritten


def test_store_business_stats_new(db_session: SQLAlchemySession):
    """Test storing business stats for the first time."""
    # Arrange: Create the parent business
    business = get_or_create_business(db_session, SAMPLE_BUSINESS_1["slug"], SAMPLE_BUSINESS_1["name"])
    db_session.commit()

    # Act
    stats = store_business_stats(db_session, business.id, SAMPLE_STATS_1)
    db_session.commit()

    # Assert
    assert stats is not None
    assert stats.business_id == business.id
    assert stats.total_reviews == SAMPLE_STATS_1["totalReviews"]
    assert stats.average_rating == float(SAMPLE_STATS_1["reviewAverage"])
    assert stats.trust_index == SAMPLE_STATS_1["monthlyStats"]["trustIndex"]
    assert stats.rating_1_count == 2
    assert stats.rating_5_count == 30
    assert stats.industry_ranking == SAMPLE_STATS_1["monthlyStats"]["industryRanking"]
    assert stats.avg_response_time == SAMPLE_STATS_1["avgResponseTime"]

    # Verify in DB
    queried_stats = db_session.query(BusinessStats).filter_by(business_id=business.id).first()
    assert queried_stats is not None
    assert queried_stats.rating_3_count == 5


def test_store_business_stats_update(db_session: SQLAlchemySession):
    """Test updating existing business stats."""
    # Arrange: Create business and store initial stats
    business = get_or_create_business(db_session, SAMPLE_BUSINESS_1["slug"], SAMPLE_BUSINESS_1["name"])
    initial_stats = store_business_stats(db_session, business.id, SAMPLE_STATS_1)
    db_session.commit()
    initial_stats_id = initial_stats.id

    # Act: Store updated stats
    updated_stats = store_business_stats(db_session, business.id, SAMPLE_STATS_2_UPDATE)
    db_session.commit()

    # Assert: Check returned object and ID
    assert updated_stats is not None
    assert updated_stats.id == initial_stats_id # Should be the same DB record
    assert updated_stats.business_id == business.id

    # Check updated values
    assert updated_stats.total_reviews == SAMPLE_STATS_2_UPDATE["totalReviews"]
    assert updated_stats.average_rating == float(SAMPLE_STATS_2_UPDATE["reviewAverage"])
    assert updated_stats.trust_index == SAMPLE_STATS_2_UPDATE["monthlyStats"]["trustIndex"]
    assert updated_stats.rating_4_count == 15 # Updated value
    assert updated_stats.rating_5_count == 35 # Updated value
    assert updated_stats.avg_response_time == SAMPLE_STATS_2_UPDATE["avgResponseTime"]

    # Verify in DB
    queried_stats = db_session.query(BusinessStats).filter_by(business_id=business.id).first()
    assert queried_stats is not None
    assert queried_stats.id == initial_stats_id
    assert queried_stats.total_reviews == 60


def test_get_latest_review_date(db_session: SQLAlchemySession):
    """Test retrieving the latest review date."""
    # Arrange
    business1 = get_or_create_business(db_session, SAMPLE_BUSINESS_1["slug"], SAMPLE_BUSINESS_1["name"])
    business2 = get_or_create_business(db_session, SAMPLE_BUSINESS_2["slug"], SAMPLE_BUSINESS_2["name"])
    review1_data = SAMPLE_REVIEW_1.copy()
    review2_data = SAMPLE_REVIEW_2.copy()
    review1_data["created_at"] = "2023-01-15 10:00:00" # Earlier
    review2_data["created_at"] = "2023-05-20 12:00:00" # Later
    review2_data["id"] = 103 # Different ID

    store_review(db_session, review1_data, business1.id)
    store_review(db_session, review2_data, business1.id) # Both reviews for business1
    db_session.commit()

    # Act
    latest_date_b1 = get_latest_review_date(db_session, SAMPLE_BUSINESS_1["slug"])
    latest_date_b2 = get_latest_review_date(db_session, SAMPLE_BUSINESS_2["slug"]) # No reviews
    latest_date_nonexistent = get_latest_review_date(db_session, "nonexistent-slug")

    # Assert
    expected_latest_date = datetime.strptime("2023-05-20 12:00:00", "%Y-%m-%d %H:%M:%S")
    assert latest_date_b1 == expected_latest_date
    assert latest_date_b2 is None
    assert latest_date_nonexistent is None


def test_get_existing_review_ids(db_session: SQLAlchemySession):
    """Test retrieving the set of existing review IDs."""
    # Arrange
    business1 = get_or_create_business(db_session, SAMPLE_BUSINESS_1["slug"], SAMPLE_BUSINESS_1["name"])
    business2 = get_or_create_business(db_session, SAMPLE_BUSINESS_2["slug"], SAMPLE_BUSINESS_2["name"])
    store_review(db_session, SAMPLE_REVIEW_1, business1.id) # id=101
    store_review(db_session, SAMPLE_REVIEW_2, business1.id) # id=102
    db_session.commit()

    # Act
    ids_b1 = get_existing_review_ids(db_session, SAMPLE_BUSINESS_1["slug"])
    ids_b2 = get_existing_review_ids(db_session, SAMPLE_BUSINESS_2["slug"])
    ids_nonexistent = get_existing_review_ids(db_session, "nonexistent-slug")

    # Assert
    assert ids_b1 == {101, 102}
    assert isinstance(ids_b1, set)
    assert ids_b2 == set()
    assert isinstance(ids_b2, set)
    assert ids_nonexistent == set()
    assert isinstance(ids_nonexistent, set)

# Note: Testing init_db directly is less common in unit tests like this,
# as the fixture already ensures tables are created. We rely on the fixture. 