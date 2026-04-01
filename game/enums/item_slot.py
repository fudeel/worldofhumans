# game/enums/item_slot.py
"""Equipment slot positions on a character."""

from enum import Enum


class ItemSlot(Enum):
    """
    Named body slot where an equippable item can be worn.

    Items of type WEAPON or ARMOR reference one of these slots
    to determine where they go on the character's paper doll.
    Non-equippable items use ``NONE``.
    """

    NONE = "none"
    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    FEET = "feet"
    HANDS = "hands"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"