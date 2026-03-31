# game/enums/faction.py
"""Faction allegiance for playable races."""

from enum import Enum


class Faction(Enum):
    """Represents the two opposing factions in the game world."""

    ALLIANCE = "Alliance"
    HORDE = "Horde"