# game/db/repositories/player_repo.py
"""Persistence operations for player characters."""

from __future__ import annotations

import json

from game.db.database import Database


class PlayerRepository:
    """
    Read and write player rows in the ``players`` table.

    Parameters
    ----------
    db:
        Active ``Database`` instance.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, player_data: dict) -> None:
        """
        Insert or replace a player row.

        *player_data* must contain keys matching the ``players`` columns.
        The ``stats_json`` value should be a plain ``dict``; it will be
        serialised automatically.
        """
        stats = player_data.get("stats_json", {})
        if isinstance(stats, dict):
            stats = json.dumps(stats)

        self._db.execute(
            """
            INSERT OR REPLACE INTO players
                (id, name, race, class, level, health, mana,
                 position_x, position_y, stats_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                player_data["id"],
                player_data["name"],
                player_data["race"],
                player_data["class"],
                player_data["level"],
                player_data["health"],
                player_data["mana"],
                player_data["position_x"],
                player_data["position_y"],
                stats,
            ),
        )
        self._db.commit()

    def load(self, player_id: str) -> dict | None:
        """
        Retrieve a player row as a ``dict``, or ``None`` if not found.

        The ``stats_json`` field is automatically deserialised.
        """
        row = self._db.fetchone(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        )
        if row is None:
            return None
        data = dict(row)
        data["stats_json"] = json.loads(data["stats_json"])
        return data

    def delete(self, player_id: str) -> None:
        """Remove a player row permanently."""
        self._db.execute("DELETE FROM players WHERE id = ?", (player_id,))
        self._db.commit()

    def list_all(self) -> list[dict]:
        """Return every player row as a list of dicts."""
        rows = self._db.fetchall("SELECT * FROM players")
        result = []
        for row in rows:
            data = dict(row)
            data["stats_json"] = json.loads(data["stats_json"])
            result.append(data)
        return result