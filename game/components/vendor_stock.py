# game/components/vendor_stock.py
"""
Single stock entry inside a vendor's inventory.

A ``VendorStockEntry`` pairs an ``Item`` with a quantity the
vendor currently has available, and a buy-price the player must
pay to purchase one unit.  The ``sell_value`` on the ``Item``
itself is what the vendor pays when the player sells *to* them.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.components.item import Item


@dataclass
class VendorStockEntry:
    """
    One line of merchandise in a vendor's stock list.

    Parameters
    ----------
    item:
        The item being offered for sale.
    quantity:
        How many units the vendor currently has.  ``-1`` means
        unlimited supply (restocks automatically).
    buy_price:
        Copper cost for the player to purchase one unit.
    """

    item: Item
    quantity: int
    buy_price: int

    # -- queries -------------------------------------------------------------

    @property
    def is_unlimited(self) -> bool:
        """``True`` if this stock line never runs out."""
        return self.quantity == -1

    @property
    def is_available(self) -> bool:
        """``True`` if at least one unit can be purchased."""
        return self.is_unlimited or self.quantity > 0

    # -- mutations -----------------------------------------------------------

    def decrement(self, amount: int = 1) -> int:
        """
        Reduce stock by *amount*.  Returns actual units removed.

        Unlimited stock is never decremented.
        """
        if self.is_unlimited:
            return amount
        taken = min(amount, self.quantity)
        self.quantity -= taken
        return taken

    def increment(self, amount: int = 1) -> None:
        """
        Increase stock by *amount*.

        Unlimited stock is unaffected.
        """
        if not self.is_unlimited:
            self.quantity += amount

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise for JSON transport to the client."""
        return {
            "item": self.item.to_dict(),
            "quantity": self.quantity,
            "buy_price": self.buy_price,
        }