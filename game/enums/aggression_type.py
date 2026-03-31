# game/enums/aggression_type.py
"""Defines how a mob reacts to nearby players."""

from enum import Enum


class AggressionType(Enum):
    """
    Controls whether a mob initiates combat unprovoked.

    AGGRESSIVE mobs attack any player who enters their
    detection range.  PASSIVE mobs ignore players until
    they are attacked first.
    """

    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"