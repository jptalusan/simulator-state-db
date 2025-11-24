"""Database connection utilities (SQLAlchemy engine/session setup).

This module creates an engine and session factory for PostgreSQL and exposes a
`get_db` dependency for FastAPI.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from simulation_db.config import DATABASE_URL
from simulation_db.models.base import Base
from simulation_db.models import State, Simulation, SimulationRun, run_state_sequence

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Set it in environment or .env")

print(f"Using DATABASE_URL: {DATABASE_URL}")
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator:
    """Yield a SQLAlchemy session, closing it after use.

    Use this as a FastAPI dependency: `Depends(get_db)`.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def drop_all_tables():
    """Drop all tables in the database.
    
    Warning: This will delete all data in the database!
    """
    # Get or create engine
    db_engine = get_engine()
    
    # Drop all tables
    Base.metadata.drop_all(bind=db_engine)
    print("All tables dropped successfully")

def get_engine():
    """Get or create the database engine."""
    global engine
    if engine is None:
        from simulation_db.config import DATABASE_URL
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not configured")
        engine = create_engine(DATABASE_URL, echo=False)
    return engine


def init_db():
    """Create all tables in the database.
    
    Call this once to set up the schema. Safe to call multiple times.
    """
    Base.metadata.create_all(bind=engine)
