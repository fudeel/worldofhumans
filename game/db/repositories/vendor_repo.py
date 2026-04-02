# game/db/repositories/vendor_repo.py
"""
Persistence operations for vendor stock definitions.

Each row links a vendor NPC (mob template) to an item with a
starting quantity and a buy-price (what the player pays).
"""

from __future__ import annotations

from game.db.database import Database


class VendorRepository:
    """
    Read and write rows in the ``vendor_stock`` table.

    Parameters
    ----------
    db:
        Active ``Database`` instance.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(
        self,
        vendor_id: str,
        item_id: str,
        quantity: int = -1,
        buy_price: int = 0,
    ) -> None:
        """
        Insert a single vendor stock entry.

        Parameters
        ----------
        vendor_id:
            Mob template id of the vendor NPC.
        item_id:
            Item catalogue id being sold.
        quantity:
            Starting quantity (``-1`` for unlimited).
        buy_price:
            Copper cost for the player to buy one unit.
        """
        self._db.execute(
            """
            INSERT INTO vendor_stock
                (vendor_id, item_id, quantity, buy_price)
            VALUES (?, ?, ?, ?)
            """,
            (vendor_id, item_id, quantity, buy_price),
        )
        self._db.commit()

    def load_by_vendor(self, vendor_id: str) -> list[dict]:
        """Return all stock entries for the given vendor."""
        rows = self._db.fetchall(
            "SELECT * FROM vendor_stock WHERE vendor_id = ?",
            (vendor_id,),
        )
        return [dict(r) for r in rows]

    def load_all(self) -> list[dict]:
        """Return every vendor stock row."""
        rows = self._db.fetchall("SELECT * FROM vendor_stock")
        return [dict(r) for r in rows]