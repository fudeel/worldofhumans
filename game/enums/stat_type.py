# game/enums/stat_type.py
"""Character attribute types used in combat calculations."""

from enum import Enum


class StatType(Enum):
    """
    All trackable character statistics.

    Primary stats (STR, AGI, STA, INT, SPI) are derived from race and
    level.  Secondary stats (HIT, CRIT, etc.) are typically granted by
    gear and buffs.
    """

    # Primary
    STRENGTH = "Strength"
    AGILITY = "Agility"
    STAMINA = "Stamina"
    INTELLECT = "Intellect"
    SPIRIT = "Spirit"

    # Secondary — offensive
    ATTACK_POWER = "Attack Power"
    SPELL_POWER = "Spell Power"
    HEALING_POWER = "Healing Power"
    HIT = "Hit"
    CRIT = "Crit"

    # Secondary — defensive
    ARMOR = "Armor"
    DEFENSE = "Defense"

    # Secondary — sustain
    MP5 = "MP5"