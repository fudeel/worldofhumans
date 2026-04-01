# game/enums/item_type.py
"""Categorisation of items that can exist in the game world."""

from enum import Enum


class ItemType(Enum):
    """
    Broad category for any item a character can possess.

    Used by the inventory and loot systems to determine
    stacking rules, equip behaviour, and tooltip display.
    """

    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    QUEST_ITEM = "quest_item"
    JUNK = "junk"