"""Database layer for badges — supports PostgreSQL (Supabase) and SQLite."""
from __future__ import annotations

import secrets
import threading
from pathlib import Path

_SQLITE_SCHEMA = """\
CREATE TABLE IF NOT EXISTS badges (
    user_id      TEXT    NOT NULL,
    github_login TEXT    NOT NULL DEFAULT '',
    token        TEXT    PRIMARY KEY,
    area_name    TEXT    NOT NULL,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_badges_user_id ON badges(user_id);

CREATE TABLE IF NOT EXISTS csv_cache (
    name       TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS badge_data_cache (
    token       TEXT PRIMARY KEY REFERENCES badges(token) ON DELETE CASCADE,
    commits     INTEGER DEFAULT 0,
    war_commits INTEGER DEFAULT 0,
    updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS area_times (
    area_name  TEXT PRIMARY KEY,
    s_24h      REAL DEFAULT 0,
    s_7d       REAL DEFAULT 0,
    s_30d      REAL DEFAULT 0,
    s_war      REAL DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

_PG_SCHEMA = """\
CREATE TABLE IF NOT EXISTS badges (
    user_id      UUID    NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    github_login TEXT    NOT NULL DEFAULT '',
    token        TEXT    PRIMARY KEY,
    area_name    TEXT    NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_badges_user_id ON badges(user_id);

CREATE TABLE IF NOT EXISTS csv_cache (
    name       TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS badge_data_cache (
    token       TEXT PRIMARY KEY REFERENCES badges(token) ON DELETE CASCADE,
    commits     INTEGER DEFAULT 0,
    war_commits INTEGER DEFAULT 0,
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS area_times (
    area_name  TEXT PRIMARY KEY,
    s_24h      REAL DEFAULT 0,
    s_7d       REAL DEFAULT 0,
    s_30d      REAL DEFAULT 0,
    s_war      REAL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);
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
            cur.execute(
                "ALTER TABLE area_times ADD COLUMN IF NOT EXISTS s_war REAL DEFAULT 0"
            )

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
    ) -> dict:
        """Create a new badge with a unique token. Returns the badge row."""
        token = secrets.token_urlsafe(12)
        self._execute(
            """INSERT INTO badges (user_id, github_login, token, area_name)
               VALUES (?, ?, ?, ?)""",
            (user_id, github_login, token, area_name),
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

    # ── Badge Data Cache ─────────────────────────────────────────────

    def save_badge_data(self, token: str, commits: int, war_commits: int = 0) -> None:
        """Cache the contribution count for a badge."""
        if self._backend == "pg":
            self._execute(
                """INSERT INTO badge_data_cache (token, commits, war_commits, updated_at)
                   VALUES (?, ?, ?, NOW())
                   ON CONFLICT (token) DO UPDATE
                   SET commits = EXCLUDED.commits, war_commits = EXCLUDED.war_commits,
                       updated_at = NOW()""",
                (token, commits, war_commits),
            )
        else:
            self._execute(
                """INSERT OR REPLACE INTO badge_data_cache (token, commits, war_commits, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                (token, commits, war_commits),
            )

    def load_badge_commits(self, token: str) -> int:
        """Load cached contribution count for a badge."""
        row = self._fetchone(
            "SELECT commits FROM badge_data_cache WHERE token = ?", (token,),
        )
        return row["commits"] if row else 0

    def load_badge_war_commits(self, token: str) -> int:
        """Load cached war-period contribution count for a badge."""
        row = self._fetchone(
            "SELECT war_commits FROM badge_data_cache WHERE token = ?", (token,),
        )
        return row["war_commits"] if row else 0

    # ── Area Times (pre-computed per-area shelter seconds) ─────────

    def save_area_times_batch(self, rows: list[tuple[str, float, float, float, float]]) -> None:
        """Bulk upsert area shelter times. Each row: (area_name, s_24h, s_7d, s_30d, s_war)."""
        for area_name, s_24h, s_7d, s_30d, s_war in rows:
            if self._backend == "pg":
                self._execute(
                    """INSERT INTO area_times (area_name, s_24h, s_7d, s_30d, s_war, updated_at)
                       VALUES (?, ?, ?, ?, ?, NOW())
                       ON CONFLICT (area_name) DO UPDATE
                       SET s_24h = EXCLUDED.s_24h, s_7d = EXCLUDED.s_7d,
                           s_30d = EXCLUDED.s_30d, s_war = EXCLUDED.s_war,
                           updated_at = NOW()""",
                    (area_name, s_24h, s_7d, s_30d, s_war),
                )
            else:
                self._execute(
                    """INSERT OR REPLACE INTO area_times (area_name, s_24h, s_7d, s_30d, s_war, updated_at)
                       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (area_name, s_24h, s_7d, s_30d, s_war),
                )

    # ── CSV Cache ──────────────────────────────────────────────────────

    def save_csv(self, name: str, content: str) -> None:
        """Persist CSV content in the database."""
        if self._backend == "pg":
            self._execute(
                """INSERT INTO csv_cache (name, content, updated_at)
                   VALUES (?, ?, NOW())
                   ON CONFLICT (name) DO UPDATE
                   SET content = EXCLUDED.content, updated_at = NOW()""",
                (name, content),
            )
        else:
            self._execute(
                """INSERT OR REPLACE INTO csv_cache (name, content, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)""",
                (name, content),
            )

    def load_csv(self, name: str) -> str | None:
        """Load cached CSV content from the database."""
        row = self._fetchone(
            "SELECT content FROM csv_cache WHERE name = ?", (name,),
        )
        return row["content"] if row else None
