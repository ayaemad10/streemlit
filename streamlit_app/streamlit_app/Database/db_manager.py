"""
db_manager.py
-------------
Handles opening and closing the SQLite database connection.
Used only by crud.py — do not modify directly.
"""

import sqlite3
import os

# Absolute path to the database file
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/database/spectrum.db")


def get_connection() -> sqlite3.Connection:
    """
    Opens and returns a connection to the SQLite database.
    Creates the database file and directory if they do not exist.
    Enables foreign key constraints and dict-style row access.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # Rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON") # Required for CASCADE DELETE to work
    return conn


def close_connection(conn: sqlite3.Connection) -> None:
    """Closes the database connection safely."""
    if conn:
        conn.close()
