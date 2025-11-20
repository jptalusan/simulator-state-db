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
    
    # Drop all tables first to ensure clean state
    # from simulation_db.database import drop_all_tables
    print("Dropping all tables...")
    # drop_all_tables()
    drop_and_recreate_database()
    print("Tables dropped.\n")
    
    # Import and run the example
    from cartpole_branching_example import main as run_example
    
    try:
        run_example()
        print("\n✓ Test completed successfully!")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def drop_and_recreate_database():
    """Drop and recreate the entire PostgreSQL database.
    
    Warning: This will destroy all data!
    """
    from sqlalchemy import create_engine, text

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
        
        # Drop the database
        conn.execute(text(f"DROP DATABASE IF EXISTS {POSTGRES_DB}"))
        print(f"Database '{POSTGRES_DB}' dropped")
        
        # Recreate it
        conn.execute(text(f"CREATE DATABASE {POSTGRES_DB}"))
        print(f"Database '{POSTGRES_DB}' recreated")
    
    admin_engine.dispose()

if __name__ == "__main__":
    main()
