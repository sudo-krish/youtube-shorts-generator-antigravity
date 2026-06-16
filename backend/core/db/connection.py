import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(_BASE_DIR, "antigravity.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

def get_db_connection():
    """Returns a new SQLite connection with dict-like row factory and WAL mode."""
    print("CONNECTING TO DB:", DB_PATH); conn = sqlite3.connect(DB_PATH, timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def execute_read_query(query: str, params: tuple = ()) -> list:
    """Executes a read query and returns a list of dictionaries."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def execute_read_one(query: str, params: tuple = ()) -> dict:
    """Executes a read query and returns a single dictionary, or None."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def execute_write_query(query: str, params: tuple = ()) -> int:
    """Executes a write query (INSERT, UPDATE, DELETE) and returns the lastrowid."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initializes the database schema using the schema.sql file."""
    if not os.path.exists(SCHEMA_PATH):
        logger.error(f"Schema file not found at {SCHEMA_PATH}")
        return

    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        
        # Apply backwards compatibility ALTERs (ignoring if column exists)
        try: cursor.execute("ALTER TABLE job_renders ADD COLUMN outputs TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE video_chunks RENAME COLUMN chunk_path TO chunk_name")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE video_chunks ADD COLUMN audio_chunk_name TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE jobs ADD COLUMN metadata TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE jobs ADD COLUMN num_chunks INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE job_stages ADD COLUMN model_id INTEGER")
        except sqlite3.OperationalError: pass
        
        conn.commit()
        logger.info(f"Initialized database successfully at {DB_PATH}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize database: {e}")
        raise e
    finally:
        conn.close()
