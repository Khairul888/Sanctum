import os
import sqlite3
from contextlib import closing
from config.config import settings

DB_PATH = settings["memory"]["db_path"]


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def add_turn(role: str, content: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO conversation_turns (role, content) VALUES (?, ?)",
            (role, content)
        )
        conn.commit()


def reset_conversation():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM conversation_turns")
        conn.commit()


def get_recent_turns(limit: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.execute(
            "SELECT role, content FROM conversation_turns ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]
