import os
import sqlite3
from contextlib import closing
from config.config import settings

DB_PATH = os.path.join(os.path.dirname(settings["memory"]["db_path"]), "applications.db")

COLUMNS = [
    "id", "title", "company", "location", "url", "salary",
    "status", "cover_letter", "filled_fields", "created_at", "updated_at",
]


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                url TEXT NOT NULL UNIQUE,
                salary TEXT,
                status TEXT NOT NULL DEFAULT 'found',
                cover_letter TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        try:
            conn.execute("ALTER TABLE job_applications ADD COLUMN filled_fields TEXT")
        except sqlite3.OperationalError:
            pass  # already added by a previous run
        conn.commit()


def _row_to_dict(row):
    return dict(zip(COLUMNS, row))


def save_job(title: str, company: str, url: str, location: str = None, salary: str = None):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            INSERT INTO job_applications (title, company, location, url, salary)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO NOTHING
            """,
            (title, company, location, url, salary),
        )
        conn.commit()
        row = conn.execute(
            f"SELECT {', '.join(COLUMNS)} FROM job_applications WHERE url = ?", (url,)
        ).fetchone()
    return _row_to_dict(row)


def get_application(application_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute(
            f"SELECT {', '.join(COLUMNS)} FROM job_applications WHERE id = ?", (application_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def update_application(application_id: int, **fields):
    if not fields:
        return get_application(application_id)
    assignments = ", ".join(f"{key} = ?" for key in fields)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            f"UPDATE job_applications SET {assignments}, updated_at = datetime('now') WHERE id = ?",
            (*fields.values(), application_id),
        )
        conn.commit()
    return get_application(application_id)


def list_applications():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        rows = conn.execute(
            f"SELECT {', '.join(COLUMNS)} FROM job_applications ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_dict(row) for row in rows]
