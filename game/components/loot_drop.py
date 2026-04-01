# game/components/loot_drop.py
"""
Temporary loot container that spawns when a mob dies.

A ``LootDrop`` is bound 1:1 to a specific dead mob instance.
It holds the rolled items and optional money.  Once the mob
respawns the drop is invalidated and players can no longer
pick anything up from it.
"""

from __future__ import annotations

from typing import Optional

from game.components.item import Item


class LootDrop:
    """
    A transient loot bag at a world position.

    Parameters
    ----------
    drop_id:
        Unique identifier (typically ``<mob_id>_loot``).
    mob_id:
        The mob template id this drop belongs to.
    position_x:
        World X coordinate where the drop appeared.
    position_y:
        World Y coordinate where the drop appeared.
    items:
        List of item references rolled on the mob's death.
    money:
        Copper coins included in the drop.
    """

    def __init__(
        self,
        drop_id: str,
        mob_id: str,
        position_x: float,
        position_y: float,
        items: Optional[list[Item]] = None,
        money: int = 0,
    ) -> None:
        self._drop_id = drop_id
        self._mob_id = mob_id
        self._x = position_x
        self._y = position_y
        self._items: list[Item] = list(items) if items else []
        self._money = max(0, money)
        self._active = True

    # -- read-only -----------------------------------------------------------

    @property
    def drop_id(self) -> str:
        return self._drop_id

    @property
    def mob_id(self) -> str:
        return self._mob_id

    @property
    def position(self) -> tuple[float, float]:
        return (self._x, self._y)

    @property
    def items(self) -> list[Item]:
        """Remaining items not yet looted."""
        return list(self._items)

    @property
    def money(self) -> int:
        """Remaining copper not yet looted."""
        return self._money

    @property
    def is_active(self) -> bool:
        """``False`` once the parent mob respawns or the drop is emptied."""
        return self._active

    @property
    def is_empty(self) -> bool:
        """``True`` when nothing remains to loot."""
        return len(self._items) == 0 and self._money == 0

    # -- mutations -----------------------------------------------------------

    def take_item(self, item_id: str) -> Optional[Item]:
        """
        Remove and return the item matching *item_id*.

        Returns ``None`` if inactive, already looted, or not found.
        """
        if not self._active:
            return None
        for i, item in enumerate(self._items):
            if item.item_id == item_id:
                return self._items.pop(i)
        return None

    def take_money(self) -> int:
        """
        Claim all remaining copper.

        Returns 0 if inactive or already looted.
        """
        if not self._active:
            return 0
        taken = self._money
        self._money = 0
        return taken

    def invalidate(self) -> None:
        """
        Mark this drop as no longer lootable.

        Called when the parent mob respawns, making the window
        for looting expire.
        """
        self._active = False

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise for JSON transport to the frontend."""
        return {
            "drop_id": self._drop_id,
            "mob_id": self._mob_id,
            "position": {"x": self._x, "y": self._y},
            "items": [it.to_dict() for it in self._items],
            "money": self._money,
            "active": self._active,
        }

    def __repr__(self) -> str:
        return (
            f"LootDrop('{self._drop_id}', items={len(self._items)}, "
            f"money={self._money}, active={self._active})"
        )