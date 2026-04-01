# game/db/repositories/loot_table_repo.py
"""Persistence operations for mob loot tables."""

from __future__ import annotations

from game.db.database import Database


class LootTableRepository:
    """
    Read and write loot-drop rows in the ``loot_tables`` table.

    Each row links a mob template to an item definition with a
    probability and quantity range.

    Parameters
    ----------
    db:
        Active ``Database`` instance.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(
        self,
        mob_template_id: str,
        item_id: str,
        drop_chance: float,
        min_quantity: int = 1,
        max_quantity: int = 1,
    ) -> None:
        """Insert a single loot entry for a mob template."""
        self._db.execute(
            """
            INSERT INTO loot_tables
                (mob_template_id, item_id, drop_chance,
                 min_quantity, max_quantity)
            VALUES (?, ?, ?, ?, ?)
            """,
            (mob_template_id, item_id, drop_chance,
             min_quantity, max_quantity),
        )
        self._db.commit()

    def load_by_mob(self, mob_template_id: str) -> list[dict]:
        """Return all loot entries for the given mob template."""
        rows = self._db.fetchall(
            "SELECT * FROM loot_tables WHERE mob_template_id = ?",
            (mob_template_id,),
        )
        return [dict(r) for r in rows]