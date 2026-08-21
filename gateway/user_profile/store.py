import os
import json
import sqlite3
from contextlib import closing
from config.config import settings

DB_PATH = os.path.join(os.path.dirname(settings["memory"]["db_path"]), "profile.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL,
                source_filename TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def get_profile():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.execute("SELECT data FROM profile WHERE id = 1")
        row = cursor.fetchone()
    return json.loads(row[0]) if row else None


def save_profile(data: dict, source_filename: str = None):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            INSERT INTO profile (id, data, source_filename, updated_at)
            VALUES (1, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                data = excluded.data,
                source_filename = COALESCE(excluded.source_filename, profile.source_filename),
                updated_at = excluded.updated_at
            """,
            (json.dumps(data), source_filename),
        )
        conn.commit()
    return data
