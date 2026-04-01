# game/world/map_object.py
"""
Base representation of a non-mob object placed on the game map.

``MapObject`` is the server-authoritative record for anything
that occupies a position and can be seen or interacted with by
players: ground items, resource nodes, NPCs, chests, levers, etc.

The backend controls creation, placement, state, and removal.
The frontend only visualises and relays player interaction
requests back to the server.
"""

from __future__ import annotations

import uuid

from game.components.vector2 import Vector2
from game.enums.interaction_type import InteractionType
from game.enums.map_object_type import MapObjectType


class MapObject:
    """
    A single placeable object on the world map.

    Parameters
    ----------
    object_id:
        Globally unique identifier.  Auto-generated when ``None``.
    name:
        Human-readable display name (e.g. "Iron Ore Vein").
    object_type:
        Category of this object (item, npc, resource_node, …).
    interaction_type:
        How a player interacts with it (loot, gather, talk, …).
    position:
        World-space coordinates where the object sits.
    zone_id:
        The zone this object belongs to.
    interaction_range:
        Maximum distance (world units) from which a player can
        interact.  Defaults to 5.0.
    respawn_sec:
        Seconds until the object reappears after being consumed.
        ``0`` means it never respawns (one-time pickup).
    metadata:
        Arbitrary key-value pairs for type-specific data
        (e.g. ``{"skill_required": "Mining", "skill_level": 50}``).
    """

    def __init__(
        self,
        *,
        object_id: str | None = None,
        name: str,
        object_type: MapObjectType,
        interaction_type: InteractionType,
        position: Vector2,
        zone_id: str,
        interaction_range: float = 5.0,
        respawn_sec: float = 0.0,
        metadata: dict | None = None,
    ) -> None:
        self._object_id = object_id or uuid.uuid4().hex[:12]
        self._name = name
        self._object_type = object_type
        self._interaction_type = interaction_type
        self._position = position
        self._zone_id = zone_id
        self._interaction_range = interaction_range
        self._respawn_sec = respawn_sec
        self._metadata = metadata or {}
        self._active = True

    # -- identity ------------------------------------------------------------

    @property
    def object_id(self) -> str:
        """Globally unique identifier."""
        return self._object_id

    @property
    def name(self) -> str:
        """Display name shown to players."""
        return self._name

    @property
    def object_type(self) -> MapObjectType:
        """Category of this map object."""
        return self._object_type

    @property
    def interaction_type(self) -> InteractionType:
        """How a player interacts with this object."""
        return self._interaction_type

    # -- spatial -------------------------------------------------------------

    @property
    def position(self) -> Vector2:
        """Current world-space position."""
        return self._position

    @position.setter
    def position(self, value: Vector2) -> None:
        self._position = value

    @property
    def zone_id(self) -> str:
        """Zone this object belongs to."""
        return self._zone_id

    @property
    def interaction_range(self) -> float:
        """Maximum interaction distance in world units."""
        return self._interaction_range

    # -- state ---------------------------------------------------------------

    @property
    def active(self) -> bool:
        """``True`` while the object is visible and interactable."""
        return self._active

    @property
    def respawn_sec(self) -> float:
        """Seconds until respawn after consumption.  0 = no respawn."""
        return self._respawn_sec

    @property
    def metadata(self) -> dict:
        """Type-specific key-value properties."""
        return self._metadata

    # -- actions -------------------------------------------------------------

    def deactivate(self) -> None:
        """Mark the object as consumed / inactive."""
        self._active = False

    def reactivate(self) -> None:
        """Restore the object after a respawn timer expires."""
        self._active = True

    def is_in_range(self, other: Vector2) -> bool:
        """Return ``True`` if *other* is within interaction range."""
        return self._position.distance_to(other) <= self._interaction_range

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Serialise to a plain dict suitable for network transmission.

        The frontend receives exactly this structure.
        """
        return {
            "object_id": self._object_id,
            "name": self._name,
            "object_type": self._object_type.value,
            "interaction_type": self._interaction_type.value,
            "position": {"x": self._position.x, "y": self._position.y},
            "zone_id": self._zone_id,
            "interaction_range": self._interaction_range,
            "active": self._active,
            "metadata": self._metadata,
        }

    # -- dunder --------------------------------------------------------------

    def __repr__(self) -> str:
        state = "active" if self._active else "inactive"
        return (
            f"MapObject('{self._object_id}', '{self._name}', "
            f"{self._object_type.value}, {state})"
        )