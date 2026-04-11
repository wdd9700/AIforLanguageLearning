"""Simple SQLite-backed user store for the auth demo.

This module provides a minimal, safe persistence layer using sqlite3.
It is intentionally small to keep the demo easy to inspect and test.
"""
from pathlib import Path
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from security_part.auth_core import hash_password

DB_PATH = Path(__file__).resolve().parent / "users.db"
_DB_LOCK = threading.Lock()


def init_db() -> None:
    """Initialize SQLite database with users table."""
    with _DB_LOCK:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT,
                    last_login TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()


init_db()


class UserStore:
    """A tiny class providing the same interface used by the routes.

    Methods match the previous `MockUserDB` used by `auth_routes.py`.
    """

    @classmethod
    def create_user(cls, username: str, email: str, password: str) -> Dict[str, Any]:
        """Create a new user with hashed password."""
        hashed = hash_password(password)
        now = datetime.now(timezone.utc).isoformat()
        with _DB_LOCK:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users (username, email, hashed_password, is_active, created_at) VALUES (?, ?, ?, ?, ?)",
                    (username, email, hashed, 1, now),
                )
                conn.commit()
                user_id = cur.lastrowid
            finally:
                conn.close()

        return {"id": user_id, "username": username, "email": email, "is_active": True, "created_at": now, "last_login": None}

    @classmethod
    def get_user_by_username(cls, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username including hashed_password."""
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, username, email, hashed_password, is_active, created_at, last_login FROM users WHERE username = ?",
                (username,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "hashed_password": row[3],
                "is_active": bool(row[4]),
                "created_at": row[5],
                "last_login": row[6],
            }
        finally:
            conn.close()

    @classmethod
    def get_user_safe(cls, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username excluding hashed_password (safe for responses)."""
        u = cls.get_user_by_username(username)
        if not u:
            return None
        return {k: v for k, v in u.items() if k != "hashed_password"}

    @classmethod
    def update_last_login(cls, username: str) -> None:
        """Update user's last login timestamp."""
        now = datetime.now(timezone.utc).isoformat()
        with _DB_LOCK:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                cur = conn.cursor()
                cur.execute("UPDATE users SET last_login = ? WHERE username = ?", (now, username))
                conn.commit()
            finally:
                conn.close()
