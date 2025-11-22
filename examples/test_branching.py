#!/usr/bin/env python3
"""Quick test runner for the branching example using SQLite.

This sets up a temporary SQLite database and runs the CartPole branching example.
"""

import os
import sys
import tempfile
# from pathlib import Path

# Setup paths
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
POSTGRES_USER = os.getenv("POSTGRES_USER", "simulation_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "change_me")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "simulation_db")

def main():
    # Use a temporary SQLite database for testing
    # db_file = Path(__file__).parent / "simulation_db.db"
    # os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    db_file = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    os.environ["DATABASE_URL"] = db_file
    
    print("=" * 80)
    print("Testing Git-Tree Simulation Structure with PostgreSQL")
    print("=" * 80)
    print(f"Database: {db_file}")
    print()
    
    # Drop and recreate tables (safer for API since server can keep its connection)
    print("Dropping and recreating tables...")
    drop_and_recreate_tables()
    print("Tables ready!")
    print()
    
    # Import and run the example
    from cartpole_branching_api_example import main as run_example
    
    try:
        run_example()
        print("\n✓ Test completed successfully!")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up database connections
        try:
            from simulation_db.database import engine as db_engine
            if db_engine:
                db_engine.dispose()
                print("\nDatabase connections closed")
        except Exception as e:
            print(f"\nNote: Could not dispose engine: {e}")

def drop_and_recreate_tables():
    """Drop and recreate all tables without dropping the database.
    
    This is safer for the API example since the FastAPI server can continue
    to use its existing database connection.
    """
    from simulation_db.database import engine as db_engine
    from simulation_db.models.base import Base
    # Import all models so they're registered with Base
    from simulation_db.models import State, Simulation, SimulationRun, run_state_sequence
    
    # Drop all tables
    Base.metadata.drop_all(bind=db_engine)
    print("All tables dropped")
    
    # Recreate all tables
    Base.metadata.create_all(bind=db_engine)
    print("All tables recreated")


def drop_and_recreate_database():
    """Drop and recreate the entire PostgreSQL database.
    
    Warning: This will destroy all data!
    Note: If using with API server, you must restart the server after this.
    """
    import time
    from sqlalchemy import create_engine, text

    # First, dispose any existing connections from the database module
    try:
        from simulation_db.database import engine as db_engine
        if db_engine:
            db_engine.dispose()
            print("Disposed existing database connections")
    except Exception as e:
        print(f"Note: Could not dispose existing engine: {e}")
    
    # Connect to 'postgres' default database (not your app database)
    admin_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    
    with admin_engine.connect() as conn:
        # Terminate all connections to the target database
        conn.execute(text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{POSTGRES_DB}'
              AND pid <> pg_backend_pid()
        """))
        
        # Give PostgreSQL a moment to clean up connections
        time.sleep(0.5)
        
        # Drop the database
        conn.execute(text(f"DROP DATABASE IF EXISTS {POSTGRES_DB}"))
        print(f"Database '{POSTGRES_DB}' dropped")
        
        # Recreate it
        conn.execute(text(f"CREATE DATABASE {POSTGRES_DB}"))
        print(f"Database '{POSTGRES_DB}' recreated")
    
    admin_engine.dispose()

if __name__ == "__main__":
    main()
