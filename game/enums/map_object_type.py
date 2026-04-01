# game/enums/map_object_type.py
"""Classification of placeable objects on the game world map."""

from enum import Enum


class MapObjectType(Enum):
    """
    Every non-mob entity that can exist at a fixed or semi-fixed
    position on the game map.

    ITEM            → lootable ground item (sword, potion, etc.).
    RESOURCE_NODE   → gatherable node (herb, ore vein, etc.).
    NPC             → non-hostile quest giver, vendor, trainer.
    INTERACTABLE    → world object the player can activate
                      (lever, chest, door, campfire, etc.).
    """

    ITEM = "item"
    RESOURCE_NODE = "resource_node"
    NPC = "npc"
    INTERACTABLE = "interactable"