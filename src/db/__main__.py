"""
LAMMR Strategy - Python entry point for database initialization.
Run: python -m src.db
"""

from src.db import init_db, get_db_path

if __name__ == "__main__":
    db_path = get_db_path("config.yaml")
    init_db(db_path)
