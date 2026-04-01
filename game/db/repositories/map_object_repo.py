# game/db/repositories/map_object_repo.py
"""
Persistence operations for map object templates.

Each row describes where an object should be placed, what
type it is, and how it behaves.  The ``ZoneController`` reads
these rows at boot and populates its ``MapObjectRegistry``.
"""

from __future__ import annotations

import json

from game.db.database import Database


class MapObjectRepository:
    """
    Read and write map-object template rows.

    Parameters
    ----------
    db:
        Active ``Database`` instance.
    """

    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS map_objects (
        id            TEXT PRIMARY KEY,
        name          TEXT    NOT NULL,
        object_type   TEXT    NOT NULL,
        interaction   TEXT    NOT NULL,
        zone_id       TEXT    NOT NULL,
        spawn_x       REAL    NOT NULL,
        spawn_y       REAL    NOT NULL,
        interact_range REAL   NOT NULL DEFAULT 5.0,
        respawn_sec   REAL    NOT NULL DEFAULT 0.0,
        metadata_json TEXT    NOT NULL DEFAULT '{}'
    )
    """

    def __init__(self, db: Database) -> None:
        self._db = db
        self._db.execute(self._CREATE_TABLE)
        self._db.commit()

    # -- write ---------------------------------------------------------------

    def save(self, data: dict) -> None:
        """
        Insert or replace a map-object template row.

        Expected keys: ``id``, ``name``, ``object_type``,
        ``interaction``, ``zone_id``, ``spawn_x``, ``spawn_y``.
        Optional: ``interact_range``, ``respawn_sec``, ``metadata``.
        """
        meta = data.get("metadata", {})
        self._db.execute(
            """
            INSERT OR REPLACE INTO map_objects
                (id, name, object_type, interaction, zone_id,
                 spawn_x, spawn_y, interact_range, respawn_sec,
                 metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["name"],
                data["object_type"],
                data["interaction"],
                data["zone_id"],
                data["spawn_x"],
                data["spawn_y"],
                data.get("interact_range", 5.0),
                data.get("respawn_sec", 0.0),
                json.dumps(meta) if isinstance(meta, dict) else meta,
            ),
        )
        self._db.commit()

    def delete(self, object_id: str) -> None:
        """Remove a map-object template by id."""
        self._db.execute(
            "DELETE FROM map_objects WHERE id = ?", (object_id,)
        )
        self._db.commit()

    # -- read ----------------------------------------------------------------

    def load(self, object_id: str) -> dict | None:
        """Retrieve a single template row as a ``dict``."""
        row = self._db.fetchone(
            "SELECT * FROM map_objects WHERE id = ?", (object_id,)
        )
        return self._row_to_dict(row) if row else None

    def load_by_zone(self, zone_id: str) -> list[dict]:
        """Return every template belonging to *zone_id*."""
        rows = self._db.fetchall(
            "SELECT * FROM map_objects WHERE zone_id = ?", (zone_id,)
        )
        return [self._row_to_dict(r) for r in rows]

    def list_all(self) -> list[dict]:
        """Return every map-object template."""
        rows = self._db.fetchall("SELECT * FROM map_objects")
        return [self._row_to_dict(r) for r in rows]

    # -- internal ------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row) -> dict:
        """Convert a database row to a plain dict with parsed metadata."""
        d = dict(row)
        raw = d.pop("metadata_json", "{}")
        d["metadata"] = json.loads(raw) if isinstance(raw, str) else raw
        return d