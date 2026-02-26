"""Database initialization and connection management."""

import sqlite3
import os
from pathlib import Path


def get_db_path(config_path: str = "config.yaml") -> str:
    """Get database path from config."""
    import yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('db_path', 'lammr.db')


def init_db(db_path: str = "lammr.db") -> sqlite3.Connection:
    """Initialize database with schema."""
    schema_path = Path(__file__).parent / "schema.sql"
    
    # Create connection
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Read and execute schema
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    # Split and execute each statement
    for statement in schema.split(';'):
        statement = statement.strip()
        if statement:
            conn.execute(statement)
    
    conn.commit()
    print(f"✓ Database initialized at {db_path}")
    return conn


def get_connection(db_path: str = "lammr.db") -> sqlite3.Connection:
    """Get a database connection."""
    if not os.path.exists(db_path):
        return init_db(db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def close_db(conn: sqlite3.Connection) -> None:
    """Close database connection."""
    if conn:
        conn.close()


def reset_db(db_path: str = "lammr.db") -> None:
    """Delete and reinitialize database (WARNING: destructive)."""
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✓ Deleted {db_path}")
    
    init_db(db_path)


if __name__ == "__main__":
    db_path = get_db_path()
    init_db(db_path)
    print(f"Database ready at {db_path}")
