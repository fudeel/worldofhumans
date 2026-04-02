# game/systems/vendor_system.py
"""
Manages vendor inventories and processes buy/sell transactions.

Each vendor NPC has a runtime stock list and a copper balance.
The ``VendorSystem`` is the single point of entry for all
vendor-related operations: querying stock, buying from a vendor,
and selling to a vendor.

Vendor stock is initialised at server boot from database seed
rows and persists in memory for the duration of the session.
"""

from __future__ import annotations

from typing import Optional

from game.components.currency import Currency
from game.components.inventory import Inventory
from game.components.item import Item
from game.components.vendor_stock import VendorStockEntry


class VendorInventory:
    """
    Runtime stock and balance for a single vendor NPC.

    Parameters
    ----------
    vendor_id:
        The mob template id that owns this inventory.
    starting_copper:
        Copper balance the vendor begins with.
    """

    def __init__(self, vendor_id: str, starting_copper: int = 0) -> None:
        self._vendor_id = vendor_id
        self._currency = Currency(copper=starting_copper)
        self._stock: list[VendorStockEntry] = []

    # -- read-only -----------------------------------------------------------

    @property
    def vendor_id(self) -> str:
        """Mob template id this inventory belongs to."""
        return self._vendor_id

    @property
    def currency(self) -> Currency:
        """The vendor's copper balance."""
        return self._currency

    @property
    def stock(self) -> list[VendorStockEntry]:
        """Current stock entries (read-only view)."""
        return list(self._stock)

    # -- stock management ----------------------------------------------------

    def add_stock(self, entry: VendorStockEntry) -> None:
        """Append a new stock entry to this vendor."""
        self._stock.append(entry)

    def find_stock_by_item_id(self, item_id: str) -> Optional[VendorStockEntry]:
        """Return the stock entry for *item_id*, or ``None``."""
        for entry in self._stock:
            if entry.item.item_id == item_id:
                return entry
        return None

    def add_item_to_stock(self, item: Item, quantity: int, buy_price: int) -> None:
        """
        Add units of an item to existing stock, or create a new entry.

        If the item already exists in stock, its quantity is increased.
        """
        existing = self.find_stock_by_item_id(item.item_id)
        if existing is not None:
            existing.increment(quantity)
        else:
            self._stock.append(
                VendorStockEntry(item=item, quantity=quantity, buy_price=buy_price)
            )

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the full vendor state for JSON transport."""
        return {
            "vendor_id": self._vendor_id,
            "currency": self._currency.to_dict(),
            "stock": [e.to_dict() for e in self._stock if e.is_available],
        }


class BuyResult:
    """
    Outcome of a player attempting to buy from a vendor.

    Parameters
    ----------
    success:
        Whether the purchase went through.
    reason:
        Human-readable failure message (empty on success).
    """

    __slots__ = ("success", "reason")

    def __init__(self, success: bool, reason: str = "") -> None:
        self.success = success
        self.reason = reason


class SellResult:
    """
    Outcome of a player attempting to sell to a vendor.

    Parameters
    ----------
    success:
        Whether the sale went through.
    reason:
        Human-readable failure message (empty on success).
    """

    __slots__ = ("success", "reason")

    def __init__(self, success: bool, reason: str = "") -> None:
        self.success = success
        self.reason = reason


class VendorSystem:
    """
    Central manager for all vendor inventories and transactions.

    Parameters
    ----------
    item_catalogue:
        Global mapping of item_id → ``Item`` for creating new
        stock entries when players sell items to vendors.
    """

    def __init__(self, item_catalogue: dict[str, Item]) -> None:
        self._items = item_catalogue
        self._vendors: dict[str, VendorInventory] = {}

    # -- registration --------------------------------------------------------

    def register_vendor(
        self,
        vendor_id: str,
        starting_copper: int = 0,
    ) -> VendorInventory:
        """
        Create and register a new vendor inventory.

        Returns the newly created ``VendorInventory``.
        """
        inv = VendorInventory(vendor_id, starting_copper)
        self._vendors[vendor_id] = inv
        return inv

    def get_vendor(self, vendor_id: str) -> Optional[VendorInventory]:
        """Return the vendor inventory, or ``None`` if not registered."""
        return self._vendors.get(vendor_id)

    # -- transactions --------------------------------------------------------

    def buy_from_vendor(
        self,
        vendor_id: str,
        item_id: str,
        player_currency: Currency,
        player_inventory: Inventory,
    ) -> BuyResult:
        """
        Player purchases one unit of *item_id* from the vendor.

        Validates: vendor exists, item in stock, player can afford,
        player has bag space.  On success, transfers copper and item.
        """
        vendor = self._vendors.get(vendor_id)
        if vendor is None:
            return BuyResult(False, "Vendor not found.")

        entry = vendor.find_stock_by_item_id(item_id)
        if entry is None or not entry.is_available:
            return BuyResult(False, "Item is not available.")

        if not player_currency.can_afford(entry.buy_price):
            return BuyResult(False, "Not enough money.")

        if player_inventory.is_full:
            leftover = player_inventory.add_item(entry.item, 0)
            if leftover == 0 and player_inventory.is_full:
                return BuyResult(False, "Inventory is full.")
            return BuyResult(False, "Inventory is full.")

        # Execute transaction
        player_currency.deduct(entry.buy_price)
        vendor.currency.add(entry.buy_price)
        entry.decrement(1)
        remaining = player_inventory.add_item(entry.item, 1)

        if remaining > 0:
            # Rollback: should not happen since we checked, but be safe
            player_currency.add(entry.buy_price)
            vendor.currency.deduct(entry.buy_price)
            entry.increment(1)
            return BuyResult(False, "Inventory is full.")

        return BuyResult(True)

    def sell_to_vendor(
        self,
        vendor_id: str,
        slot_index: int,
        player_currency: Currency,
        player_inventory: Inventory,
    ) -> SellResult:
        """
        Player sells one unit from *slot_index* to the vendor.

        The vendor pays the item's ``sell_value``.  If the vendor
        has insufficient funds the sale is refused.
        """
        vendor = self._vendors.get(vendor_id)
        if vendor is None:
            return SellResult(False, "Vendor not found.")

        slot = player_inventory.slots[slot_index] if 0 <= slot_index < player_inventory.capacity else None
        if slot is None:
            return SellResult(False, "No item in that slot.")

        item = slot.item
        sell_price = item.sell_value

        if sell_price <= 0:
            return SellResult(False, "This item cannot be sold.")

        if not vendor.currency.can_afford(sell_price):
            return SellResult(False, "Vendor does not have enough money for this item.")

        # Execute transaction
        removed = player_inventory.remove_item_at(slot_index, 1)
        if removed is None:
            return SellResult(False, "Failed to remove item.")

        vendor.currency.deduct(sell_price)
        player_currency.add(sell_price)

        # Add the sold item to the vendor's stock so other players can buy it
        # Price it at double the sell_value (standard vendor markup)
        vendor.add_item_to_stock(item, 1, sell_price * 2)

        return SellResult(True)