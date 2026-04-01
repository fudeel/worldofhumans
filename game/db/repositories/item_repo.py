# game/db/repositories/item_repo.py
"""Persistence operations for the game item catalogue."""

from __future__ import annotations

import json

from game.db.database import Database


class ItemRepository:
    """
    Read and write rows in the ``items`` table.

    Parameters
    ----------
    db:
        Active ``Database`` instance.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, data: dict) -> None:
        """Insert or replace an item definition row."""
        bonuses = data.get("stat_bonuses", {})
        if isinstance(bonuses, dict):
            bonuses = json.dumps(bonuses)

        self._db.execute(
            """
            INSERT OR REPLACE INTO items
                (id, name, item_type, sell_value, slot,
                 stat_bonuses, description, stackable,
                 max_stack, level_req)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["name"],
                data.get("item_type", "junk"),
                data.get("sell_value", 0),
                data.get("slot", "none"),
                bonuses,
                data.get("description", ""),
                int(data.get("stackable", False)),
                data.get("max_stack", 1),
                data.get("level_req", 1),
            ),
        )
        self._db.commit()

    def load(self, item_id: str) -> dict | None:
        """Retrieve a single item row as a dict, or ``None``."""
        row = self._db.fetchone(
            "SELECT * FROM items WHERE id = ?", (item_id,)
        )
        if row is None:
            return None
        d = dict(row)
        d["stat_bonuses"] = json.loads(d["stat_bonuses"])
        d["stackable"] = bool(d["stackable"])
        return d

    def load_all(self) -> list[dict]:
        """Return every item in the catalogue."""
        rows = self._db.fetchall("SELECT * FROM items")
        result = []
        for row in rows:
            d = dict(row)
            d["stat_bonuses"] = json.loads(d["stat_bonuses"])
            d["stackable"] = bool(d["stackable"])
            result.append(d)
        return result