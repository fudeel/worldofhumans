# game/db/repositories/zone_repo.py
"""Persistence operations for gaming zone configurations."""

from __future__ import annotations

from game.db.database import Database


class ZoneRepository:
    """
    Read and write zone rows in the ``zones`` table.

    Parameters
    ----------
    db:
        Active ``Database`` instance.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, zone_data: dict) -> None:
        """Insert or replace a zone configuration row."""
        self._db.execute(
            """
            INSERT OR REPLACE INTO zones
                (id, name, chunk_size, min_x, min_y, max_x, max_y)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                zone_data["id"],
                zone_data["name"],
                zone_data["chunk_size"],
                zone_data["min_x"],
                zone_data["min_y"],
                zone_data["max_x"],
                zone_data["max_y"],
            ),
        )
        self._db.commit()

    def load(self, zone_id: str) -> dict | None:
        """Retrieve a single zone row as a ``dict``, or ``None``."""
        row = self._db.fetchone(
            "SELECT * FROM zones WHERE id = ?", (zone_id,)
        )
        return dict(row) if row else None

    def list_all(self) -> list[dict]:
        """Return every zone configuration."""
        return [dict(r) for r in self._db.fetchall("SELECT * FROM zones")]