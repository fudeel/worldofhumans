# game/db/database.py
"""
SQLite connection manager.

Provides a single shared connection for the game server process.
All writes flow through the game loop, so the single-writer
constraint of SQLite is never a concern.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from game.db.schema import ALL_TABLES

_DEFAULT_DB_PATH = "game_world.db"


class Database:
    """
    Manages the SQLite connection and schema migrations.

    Parameters
    ----------
    db_path:
        Filesystem path for the database file.
        Use ``":memory:"`` for ephemeral test databases.
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        self._path = db_path
        self._conn: sqlite3.Connection | None = None

    # -- lifecycle -----------------------------------------------------------

    def connect(self) -> None:
        """Open the database connection and apply migrations."""
        self._conn = sqlite3.connect(self._path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._migrate()

    def close(self) -> None:
        """Flush and close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # -- access --------------------------------------------------------------

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the active connection or raise if not connected."""
        if self._conn is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single SQL statement and return the cursor."""
        return self.connection.execute(sql, params)

    def executemany(self, sql: str, seq: list[tuple]) -> sqlite3.Cursor:
        """Execute a SQL statement against a sequence of parameter tuples."""
        return self.connection.executemany(sql, seq)

    def commit(self) -> None:
        """Commit the current transaction."""
        self.connection.commit()

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Execute and return a single row, or ``None``."""
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute and return all matching rows."""
        return self.execute(sql, params).fetchall()

    # -- internal ------------------------------------------------------------

    def _migrate(self) -> None:
        """Create all tables if they do not already exist."""
        for ddl in ALL_TABLES:
            self.connection.execute(ddl)
        self.commit()