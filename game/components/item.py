# game/components/item.py
"""
Immutable blueprint for a single game item.

An ``Item`` describes what something *is* — its name, category,
value, and stat bonuses.  It does not track quantity or ownership;
that responsibility belongs to the ``Inventory`` component.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game.enums.item_slot import ItemSlot
from game.enums.item_type import ItemType


@dataclass(frozen=True)
class Item:
    """
    Static description of a game item.

    Parameters
    ----------
    item_id:
        Unique identifier across the entire item catalogue.
    name:
        Human-readable display name (e.g. "Rusty Sword").
    item_type:
        Broad category (weapon, armor, consumable, …).
    sell_value:
        Base copper-coin value when sold to a vendor.
    slot:
        Equipment slot this item occupies (``NONE`` if not equippable).
    stat_bonuses:
        Mapping of stat-name → bonus value granted while equipped.
    description:
        Flavour text shown in the item tooltip.
    stackable:
        Whether multiple copies can occupy one inventory slot.
    max_stack:
        Maximum units per stack (only meaningful when stackable).
    level_req:
        Minimum character level required to use or equip.
    """

    item_id: str
    name: str
    item_type: ItemType
    sell_value: int = 0
    slot: ItemSlot = ItemSlot.NONE
    stat_bonuses: dict[str, int] = field(default_factory=dict)
    description: str = ""
    stackable: bool = False
    max_stack: int = 1
    level_req: int = 1

    # -- queries -------------------------------------------------------------

    @property
    def is_equippable(self) -> bool:
        """``True`` if this item can be worn in an equipment slot."""
        return self.slot is not ItemSlot.NONE

    @property
    def is_stackable(self) -> bool:
        """``True`` if multiple units share a single slot."""
        return self.stackable and self.max_stack > 1

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for JSON transport."""
        return {
            "item_id": self.item_id,
            "name": self.name,
            "item_type": self.item_type.value,
            "sell_value": self.sell_value,
            "slot": self.slot.value,
            "stat_bonuses": dict(self.stat_bonuses),
            "description": self.description,
            "stackable": self.stackable,
            "max_stack": self.max_stack,
            "level_req": self.level_req,
        }

    def __str__(self) -> str:
        return f"[{self.item_type.value}] {self.name}"