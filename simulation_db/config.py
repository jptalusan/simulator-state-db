"""Configuration helpers for `simulation_db`.

Load environment variables and expose configuration values (e.g., `DATABASE_URL`).
"""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# Allow explicit `DATABASE_URL` override; otherwise build from POSTGRES_* vars
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
	_user = os.getenv("POSTGRES_USER")
	_password = os.getenv("POSTGRES_PASSWORD")
	_port = os.getenv("POSTGRES_PORT")
	_db = os.getenv("POSTGRES_DB")
	_host = os.getenv("POSTGRES_HOST", "localhost")
	if _user and _password and _port and _db:
		DATABASE_URL = f"postgresql://{_user}:{_password}@{_host}:{_port}/{_db}"
