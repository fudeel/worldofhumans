# game/world/map_object_registry.py
"""
Centralized registry for all non-mob objects within a zone.

Each ``ZoneController`` owns one ``MapObjectRegistry``.  It
handles placement, removal, respawn timers, and provides the
snapshot that gets broadcast to nearby players every tick.
"""

from __future__ import annotations

from collections import deque

from game.components.vector2 import Vector2
from game.world.map_object import MapObject


class _RespawnTimer:
    """Tracks a consumed map object awaiting respawn."""

    __slots__ = ("map_object", "remaining")

    def __init__(self, map_object: MapObject, delay: float) -> None:
        self.map_object = map_object
        self.remaining = delay


class MapObjectRegistry:
    """
    Owns every ``MapObject`` in a single zone.

    Responsibilities:

    * Store and index active objects by id.
    * Provide a snapshot list for the sync system.
    * Drive respawn timers each tick.
    * Range-check player interactions.

    Parameters
    ----------
    zone_id:
        The zone this registry belongs to.
    """

    def __init__(self, zone_id: str) -> None:
        self._zone_id = zone_id
        self._objects: dict[str, MapObject] = {}
        self._respawn_queue: deque[_RespawnTimer] = deque()

    # -- queries -------------------------------------------------------------

    @property
    def zone_id(self) -> str:
        """Zone this registry serves."""
        return self._zone_id

    @property
    def count(self) -> int:
        """Total registered objects (active + inactive)."""
        return len(self._objects)

    def get(self, object_id: str) -> MapObject | None:
        """Retrieve an object by id, or ``None``."""
        return self._objects.get(object_id)

    def get_active(self) -> list[MapObject]:
        """Return every currently active (visible) object."""
        return [o for o in self._objects.values() if o.active]

    def get_all(self) -> list[MapObject]:
        """Return every registered object regardless of state."""
        return list(self._objects.values())

    # -- mutation ------------------------------------------------------------

    def register(self, obj: MapObject) -> None:
        """
        Add an object to this zone's registry.

        Overwrites any existing object with the same id.
        """
        self._objects[obj.object_id] = obj

    def remove(self, object_id: str) -> MapObject | None:
        """
        Permanently remove an object.  Returns it, or ``None``.

        Unlike ``consume``, a removed object will *not* respawn.
        """
        return self._objects.pop(object_id, None)

    def consume(self, object_id: str) -> MapObject | None:
        """
        Mark an object as consumed (looted, gathered, activated).

        If the object has a non-zero ``respawn_sec``, it is queued
        for automatic reactivation.  Returns the object, or
        ``None`` if the id is unknown or already inactive.
        """
        obj = self._objects.get(object_id)
        if obj is None or not obj.active:
            return None
        obj.deactivate()
        if obj.respawn_sec > 0:
            self._respawn_queue.append(
                _RespawnTimer(obj, obj.respawn_sec)
            )
        return obj

    # -- tick ----------------------------------------------------------------

    def update(self, dt: float) -> list[MapObject]:
        """
        Advance respawn timers and reactivate ready objects.

        Returns the list of objects that just respawned this tick
        so the caller can broadcast the event.
        """
        respawned: list[MapObject] = []
        still_waiting: deque[_RespawnTimer] = deque()
        for timer in self._respawn_queue:
            timer.remaining -= dt
            if timer.remaining <= 0:
                timer.map_object.reactivate()
                respawned.append(timer.map_object)
            else:
                still_waiting.append(timer)
        self._respawn_queue = still_waiting
        return respawned

    # -- range check ---------------------------------------------------------

    def get_interactable_at(
        self, position: Vector2
    ) -> list[MapObject]:
        """
        Return active objects within interaction range of *position*.

        Useful for the frontend to highlight clickable objects and
        for the server to validate interaction requests.
        """
        return [
            o for o in self._objects.values()
            if o.active and o.is_in_range(position)
        ]

    # -- serialisation -------------------------------------------------------

    def snapshot(self) -> list[dict]:
        """
        Serialise every active object for network transmission.

        Called by the sync system each tick alongside entity data.
        """
        return [o.to_dict() for o in self._objects.values() if o.active]

    def __repr__(self) -> str:
        active = sum(1 for o in self._objects.values() if o.active)
        return (
            f"MapObjectRegistry(zone='{self._zone_id}', "
            f"total={len(self._objects)}, active={active})"
        )