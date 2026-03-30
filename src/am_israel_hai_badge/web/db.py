"""Database layer for badges — supports PostgreSQL (Supabase) and SQLite."""
from __future__ import annotations

import json
import secrets
import threading
from pathlib import Path

_SQLITE_SCHEMA = """\
CREATE TABLE IF NOT EXISTS badges (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      TEXT    NOT NULL,
    github_login TEXT    NOT NULL DEFAULT '',
    github_token TEXT    NOT NULL DEFAULT '',
    token        TEXT    UNIQUE NOT NULL,
    area_names   TEXT    NOT NULL,
    label        TEXT,
    show_commits INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_badges_token   ON badges(token);
CREATE INDEX IF NOT EXISTS idx_badges_user_id ON badges(user_id);
"""

_PG_SCHEMA = """\
CREATE TABLE IF NOT EXISTS badges (
    id           SERIAL PRIMARY KEY,
    user_id      TEXT    NOT NULL,
    github_login TEXT    NOT NULL DEFAULT '',
    github_token TEXT    NOT NULL DEFAULT '',
    token        TEXT    UNIQUE NOT NULL,
    area_names   TEXT    NOT NULL,
    label        TEXT,
    show_commits INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_badges_token   ON badges(token);
CREATE INDEX IF NOT EXISTS idx_badges_user_id ON badges(user_id);
"""


class Database:
    """Thin wrapper supporting both SQLite (local dev) and PostgreSQL (Supabase).

    If *dsn* starts with ``postgres://`` or ``postgresql://``, psycopg2 is used.
    Otherwise it is treated as a SQLite path (or ``":memory:"`` for tests).
    """

    def __init__(self, dsn: str | Path = ":memory:") -> None:
        self._lock = threading.Lock()
        dsn_str = str(dsn)
        if dsn_str.startswith(("postgres://", "postgresql://")):
            self._init_pg(dsn_str)
        else:
            self._init_sqlite(dsn_str)

    # ── Backends ──────────────────────────────────────────────────────

    def _init_pg(self, url: str) -> None:
        import psycopg2  # type: ignore[import-untyped]

        self._backend = "pg"
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        self._conn = psycopg2.connect(url)
        self._conn.autocommit = True
        with self._conn.cursor() as cur:
            cur.execute(_PG_SCHEMA)
            # Migration: add github_token if missing (for existing tables)
            cur.execute("""
                ALTER TABLE badges ADD COLUMN IF NOT EXISTS
                    github_token TEXT NOT NULL DEFAULT ''
            """)

    def _init_sqlite(self, path: str) -> None:
        import sqlite3

        self._backend = "sqlite"
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SQLITE_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # ── Internal helpers ──────────────────────────────────────────────

    def _q(self, sql: str) -> str:
        """Convert ``?`` placeholders to ``%s`` for PostgreSQL."""
        if self._backend == "pg":
            return sql.replace("?", "%s")
        return sql

    def _fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        with self._lock:
            if self._backend == "pg":
                import psycopg2.extras  # type: ignore[import-untyped]

                with self._conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor,
                ) as cur:
                    cur.execute(self._q(sql), params)
                    row = cur.fetchone()
                    return dict(row) if row else None
            else:
                row = self._conn.execute(sql, params).fetchone()
                return dict(row) if row else None

    def _fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            if self._backend == "pg":
                import psycopg2.extras  # type: ignore[import-untyped]

                with self._conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor,
                ) as cur:
                    cur.execute(self._q(sql), params)
                    return [dict(r) for r in cur.fetchall()]
            else:
                return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def _execute(self, sql: str, params: tuple = ()) -> int:
        """Execute a write query. Returns rowcount."""
        with self._lock:
            if self._backend == "pg":
                with self._conn.cursor() as cur:
                    cur.execute(self._q(sql), params)
                    return cur.rowcount
            else:
                cur = self._conn.execute(sql, params)
                self._conn.commit()
                return cur.rowcount

    # ── Badges ────────────────────────────────────────────────────────

    def create_badge(
        self,
        user_id: str,
        github_login: str,
        area_name: str,
        github_token: str = "",
        label: str = "",
        show_commits: bool = False,
    ) -> dict:
        """Create a new badge with a unique token. Returns the badge row."""
        token = secrets.token_urlsafe(12)
        self._execute(
            """INSERT INTO badges (user_id, github_login, github_token, token, area_names, label, show_commits)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, github_login, github_token, token,
             json.dumps(area_name, ensure_ascii=False), label, int(show_commits)),
        )
        return self.get_badge_by_token(token)  # type: ignore[return-value]

    def get_badge_by_token(self, token: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM badges WHERE token = ?", (token,),
        )

    def list_badges_for_user(self, user_id: str) -> list[dict]:
        return self._fetchall(
            "SELECT * FROM badges WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )

    def delete_badge(self, token: str, user_id: str) -> bool:
        """Delete a badge if it belongs to the given user. Returns True if deleted."""
        rowcount = self._execute(
            "DELETE FROM badges WHERE token = ? AND user_id = ?", (token, user_id),
        )
        return rowcount > 0
