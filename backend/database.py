# Database configuration module that initializes SQLAlchemy engine, session, and base model.
# Manages connection to PostgreSQL and provides a reusable dependency for safe DB access in routes.


from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Create the SQLAlchemy engine connected to Supabase PostgreSQL
engine = create_engine(settings.DATABASE_URL)

# Each request gets its own session, closed when done
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All models inherit from this Base
Base = declarative_base()


def get_db():
    """
    Dependency — inject this into any route that needs DB access.
    Usage:  db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()