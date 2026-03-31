# game/db/repositories/loot_table_repo.py
"""Persistence operations for mob loot tables."""

from __future__ import annotations

from game.db.database import Database


class LootTableRepository:
    """
    Read and write loot-drop rows in the ``loot_tables`` table.

    Parameters
    ----------
    db:
        Active ``Database`` instance.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, mob_template_id: str, item_name: str, drop_chance: float) -> None:
        """Insert a single loot entry for a mob template."""
        self._db.execute(
            """
            INSERT INTO loot_tables (mob_template_id, item_name, drop_chance)
            VALUES (?, ?, ?)
            """,
            (mob_template_id, item_name, drop_chance),
        )
        self._db.commit()

    def load_by_mob(self, mob_template_id: str) -> list[dict]:
        """Return all loot entries for the given mob template."""
        rows = self._db.fetchall(
            "SELECT * FROM loot_tables WHERE mob_template_id = ?",
            (mob_template_id,),
        )
        return [dict(r) for r in rows]