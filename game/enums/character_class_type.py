# game/enums/character_class_type.py
"""Playable character class identifiers."""

from enum import Enum


class CharacterClassType(Enum):
    """The nine playable classes available in Classic WoW."""

    HUNTER = "Hunter"
    MAGE = "Mage"
    DRUID = "Druid"
    PALADIN = "Paladin"
    PRIEST = "Priest"
    ROGUE = "Rogue"
    SHAMAN = "Shaman"
    WARLOCK = "Warlock"
    WARRIOR = "Warrior"