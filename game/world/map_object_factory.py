# game/world/map_object_factory.py
"""
Constructs ``MapObject`` instances from database template rows.

Centralises the mapping between raw dict rows (from
``MapObjectRepository``) and fully typed ``MapObject`` instances
so that construction logic lives in one place.
"""

from __future__ import annotations

from game.components.vector2 import Vector2
from game.enums.interaction_type import InteractionType
from game.enums.map_object_type import MapObjectType
from game.world.map_object import MapObject


class MapObjectFactory:
    """
    Stateless factory for ``MapObject`` creation.

    Usage::

        obj = MapObjectFactory.from_template(row)
    """

    @staticmethod
    def from_template(template: dict) -> MapObject:
        """
        Build a ``MapObject`` from a database template row.

        Expected keys: ``id``, ``name``, ``object_type``,
        ``interaction``, ``zone_id``, ``spawn_x``, ``spawn_y``.
        Optional: ``interact_range``, ``respawn_sec``, ``metadata``.
        """
        return MapObject(
            object_id=template["id"],
            name=template["name"],
            object_type=MapObjectType(template["object_type"]),
            interaction_type=InteractionType(template["interaction"]),
            position=Vector2(template["spawn_x"], template["spawn_y"]),
            zone_id=template["zone_id"],
            interaction_range=float(template.get("interact_range", 5.0)),
            respawn_sec=float(template.get("respawn_sec", 0.0)),
            metadata=template.get("metadata", {}),
        )