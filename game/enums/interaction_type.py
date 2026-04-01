# game/enums/interaction_type.py
"""Types of player interactions with map objects."""

from enum import Enum


class InteractionType(Enum):
    """
    Describes how a player engages with a ``MapObject``.

    LOOT    → pick up an item from the ground.
    GATHER  → harvest a resource node (herb, ore, etc.).
    TALK    → open dialogue with an NPC.
    ACTIVATE→ trigger a world object (open chest, pull lever).
    """

    LOOT = "loot"
    GATHER = "gather"
    TALK = "talk"
    ACTIVATE = "activate"