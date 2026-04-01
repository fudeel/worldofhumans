# game/systems/interaction_system.py
"""
Processes player interaction requests with map objects.

Validates range, checks object state, and delegates the
consumption to the ``MapObjectRegistry``.  Returns a result
dict that the network layer translates into a client message.
"""

from __future__ import annotations

from game.components.vector2 import Vector2
from game.world.map_object import MapObject
from game.world.map_object_registry import MapObjectRegistry
from game.world.world import World


class InteractionResult:
    """
    Outcome of a player's interaction attempt.

    Parameters
    ----------
    success:
        Whether the interaction was carried out.
    object_data:
        Serialised map-object dict (present on success).
    reason:
        Human-readable failure reason (present on failure).
    """

    __slots__ = ("success", "object_data", "reason")

    def __init__(
        self,
        success: bool,
        object_data: dict | None = None,
        reason: str = "",
    ) -> None:
        self.success = success
        self.object_data = object_data
        self.reason = reason

    def to_dict(self) -> dict:
        """Serialise for network transmission."""
        d: dict = {"success": self.success}
        if self.object_data:
            d["object"] = self.object_data
        if self.reason:
            d["reason"] = self.reason
        return d


class InteractionSystem:
    """
    Validates and executes player interactions with map objects.

    One instance is shared across all zones.  Each call specifies
    which registry to use.

    Parameters
    ----------
    world:
        Provides entity position lookups.
    """

    def __init__(self, world: World) -> None:
        self._world = world

    def interact(
        self,
        player_id: str,
        object_id: str,
        registry: MapObjectRegistry,
    ) -> InteractionResult:
        """
        Attempt to interact with a map object.

        Checks:
        1. Player exists and has a known position.
        2. Object exists and is active.
        3. Player is within interaction range.

        On success the object is consumed via the registry.
        """
        player_pos = self._world.get_entity_position(player_id)
        if player_pos is None:
            return InteractionResult(False, reason="Player not found.")

        obj = registry.get(object_id)
        if obj is None:
            return InteractionResult(False, reason="Object not found.")
        if not obj.active:
            return InteractionResult(False, reason="Object is not available.")

        pv = Vector2(player_pos[0], player_pos[1])
        if not obj.is_in_range(pv):
            return InteractionResult(
                False,
                reason="Too far away to interact.",
            )

        data = obj.to_dict()
        registry.consume(object_id)
        return InteractionResult(True, object_data=data)