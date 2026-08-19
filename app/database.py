"""
Database configuration for the Medication Management App.

Sets up a SQLite database connection using SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database URL — the .db file will be created in the project root
SQLALCHEMY_DATABASE_URL = "sqlite:///./medication_app.db"

# Create the SQLAlchemy engine
# connect_args={"check_same_thread": False} is required for SQLite
# to allow multiple threads to access the same connection
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Each instance of SessionLocal will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative ORM models
Base = declarative_base()


def get_db():
    """
    Dependency that provides a database session per request.

    Yields a SQLAlchemy session and ensures it is closed after use.
    Use this with FastAPI's Depends() for route injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
