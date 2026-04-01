# game/components/inventory.py
"""
Fixed-size item container bound 1:1 to a character.

The ``Inventory`` manages a flat list of slots.  Each slot is
either empty (``None``) or holds an ``InventorySlot`` with an
item reference and a quantity.  The default capacity is 8 but
can be expanded at runtime (e.g. bag upgrades).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from game.components.item import Item


DEFAULT_CAPACITY = 8
"""Starting number of inventory slots every character gets."""


@dataclass
class InventorySlot:
    """
    One occupied position inside an inventory.

    Attributes
    ----------
    item:
        The item stored in this slot.
    quantity:
        How many units of the item are stacked here.
    """

    item: Item
    quantity: int = 1

    def to_dict(self) -> dict:
        """Serialise for JSON transport."""
        return {
            "item": self.item.to_dict(),
            "quantity": self.quantity,
        }


class Inventory:
    """
    Slot-based item container with a configurable capacity.

    Parameters
    ----------
    capacity:
        Maximum number of slots.  Defaults to ``DEFAULT_CAPACITY``.
    """

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self._capacity = capacity
        self._slots: list[Optional[InventorySlot]] = [None] * capacity

    # -- read-only properties ------------------------------------------------

    @property
    def capacity(self) -> int:
        """Total number of slots (occupied + empty)."""
        return self._capacity

    @property
    def used_slots(self) -> int:
        """Number of occupied slots."""
        return sum(1 for s in self._slots if s is not None)

    @property
    def free_slots(self) -> int:
        """Number of empty slots."""
        return self._capacity - self.used_slots

    @property
    def is_full(self) -> bool:
        """``True`` when every slot is occupied."""
        return self.free_slots == 0

    @property
    def slots(self) -> list[Optional[InventorySlot]]:
        """Read-only view of the internal slot list."""
        return list(self._slots)

    # -- mutations -----------------------------------------------------------

    def add_item(self, item: Item, quantity: int = 1) -> int:
        """
        Try to place *quantity* units of *item* into the inventory.

        Stackable items fill existing partial stacks first, then
        overflow into empty slots.  Non-stackable items each consume
        one slot.

        Returns the number of units that could **not** be stored
        (0 means everything fit).
        """
        remaining = quantity

        if item.is_stackable:
            remaining = self._stack_into_existing(item, remaining)

        while remaining > 0:
            idx = self._first_empty_slot()
            if idx is None:
                break
            if item.is_stackable:
                fit = min(remaining, item.max_stack)
                self._slots[idx] = InventorySlot(item=item, quantity=fit)
                remaining -= fit
            else:
                self._slots[idx] = InventorySlot(item=item, quantity=1)
                remaining -= 1

        return remaining

    def remove_item_at(self, slot_index: int, quantity: int = 1) -> Optional[InventorySlot]:
        """
        Remove *quantity* units from slot *slot_index*.

        Returns the removed ``InventorySlot`` snapshot, or ``None``
        if the slot was empty or the index is invalid.
        """
        if not self._valid_index(slot_index):
            return None
        slot = self._slots[slot_index]
        if slot is None:
            return None

        removed_qty = min(quantity, slot.quantity)
        removed = InventorySlot(item=slot.item, quantity=removed_qty)

        slot.quantity -= removed_qty
        if slot.quantity <= 0:
            self._slots[slot_index] = None

        return removed

    def remove_item_by_id(self, item_id: str, quantity: int = 1) -> int:
        """
        Remove up to *quantity* units of the item with *item_id*.

        Scans all slots and removes units until the target is met.
        Returns the number of units actually removed.
        """
        removed = 0
        for i, slot in enumerate(self._slots):
            if removed >= quantity:
                break
            if slot is not None and slot.item.item_id == item_id:
                take = min(quantity - removed, slot.quantity)
                slot.quantity -= take
                removed += take
                if slot.quantity <= 0:
                    self._slots[i] = None
        return removed

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """``True`` if the inventory contains at least *quantity* of *item_id*."""
        return self.count_item(item_id) >= quantity

    def count_item(self, item_id: str) -> int:
        """Total units of *item_id* across all slots."""
        return sum(
            s.quantity for s in self._slots
            if s is not None and s.item.item_id == item_id
        )

    def expand(self, extra_slots: int) -> None:
        """
        Increase capacity by *extra_slots*.

        Used when the character acquires a larger bag.
        """
        if extra_slots <= 0:
            return
        self._capacity += extra_slots
        self._slots.extend([None] * extra_slots)

    def clear(self) -> list[InventorySlot]:
        """Remove and return all occupied slots."""
        removed = [s for s in self._slots if s is not None]
        self._slots = [None] * self._capacity
        return removed

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the full inventory state for JSON transport."""
        return {
            "capacity": self._capacity,
            "slots": [
                s.to_dict() if s is not None else None
                for s in self._slots
            ],
        }

    # -- internals -----------------------------------------------------------

    def _stack_into_existing(self, item: Item, remaining: int) -> int:
        """Try to merge units into existing partial stacks."""
        for slot in self._slots:
            if remaining <= 0:
                break
            if (
                slot is not None
                and slot.item.item_id == item.item_id
                and slot.quantity < item.max_stack
            ):
                space = item.max_stack - slot.quantity
                fit = min(remaining, space)
                slot.quantity += fit
                remaining -= fit
        return remaining

    def _first_empty_slot(self) -> Optional[int]:
        """Return the index of the first empty slot, or ``None``."""
        for i, s in enumerate(self._slots):
            if s is None:
                return i
        return None

    def _valid_index(self, idx: int) -> bool:
        return 0 <= idx < self._capacity

    def __repr__(self) -> str:
        return f"Inventory({self.used_slots}/{self._capacity})"