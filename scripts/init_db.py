"""Script to initialize DB schema (create all tables).

Usage:
    python scripts/init_db.py
    
This will create all tables defined in the ORM models.
Safe to run multiple times - won't drop existing data.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulation_db.database import init_db


def main():
    print("Initializing database schema...")
    print("This will create all tables if they don't exist.")
    
    try:
        init_db()
        print("✓ Database initialized successfully!")
        print("\nTables created:")
        print("  - simulations")
        print("  - simulation_runs")
        print("  - states")
        print("  - run_state_sequence (association table)")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
