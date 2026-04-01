# game/components/currency.py
"""
Copper-based monetary system bound 1:1 to a character.

All values are stored internally as copper (the smallest unit).
Convenience properties convert to silver and gold using the
classic 100-copper-per-silver, 100-silver-per-gold ratio.
"""

from __future__ import annotations


class Currency:
    """
    Holds and manipulates a character's money balance.

    Every character starts at zero copper.  Money is earned
    through quest rewards, looting dead enemies, or selling
    items.

    Parameters
    ----------
    copper:
        Initial copper amount (default 0).
    """

    COPPER_PER_SILVER = 100
    COPPER_PER_GOLD = 10_000  # 100 silver × 100 copper

    def __init__(self, copper: int = 0) -> None:
        self._copper = max(0, copper)

    # -- read-only -----------------------------------------------------------

    @property
    def total_copper(self) -> int:
        """Raw copper balance."""
        return self._copper

    @property
    def gold(self) -> int:
        """Whole gold coins in the balance."""
        return self._copper // self.COPPER_PER_GOLD

    @property
    def silver(self) -> int:
        """Remaining silver after extracting gold."""
        return (self._copper % self.COPPER_PER_GOLD) // self.COPPER_PER_SILVER

    @property
    def copper(self) -> int:
        """Remaining copper after extracting gold and silver."""
        return self._copper % self.COPPER_PER_SILVER

    # -- mutations -----------------------------------------------------------

    def add(self, copper: int) -> None:
        """
        Credit *copper* to the balance.

        Negative amounts are silently ignored to prevent exploits.
        """
        if copper > 0:
            self._copper += copper

    def deduct(self, copper: int) -> bool:
        """
        Debit *copper* from the balance if funds are sufficient.

        Returns ``True`` on success, ``False`` if the character
        cannot afford the transaction.
        """
        if copper <= 0:
            return True
        if self._copper < copper:
            return False
        self._copper -= copper
        return True

    def can_afford(self, copper: int) -> bool:
        """``True`` if the balance covers *copper*."""
        return self._copper >= copper

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise for JSON transport."""
        return {
            "total_copper": self._copper,
            "gold": self.gold,
            "silver": self.silver,
            "copper": self.copper,
        }

    def __repr__(self) -> str:
        return f"Currency({self.gold}g {self.silver}s {self.copper}c)"