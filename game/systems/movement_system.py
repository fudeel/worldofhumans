# game/systems/movement_system.py
"""
Processes movement intents and enforces zone-gate logic.

When a player moves into a gaming zone the server begins
streaming world data.  When they leave, streaming stops
and they see only their own character.
"""

from __future__ import annotations

from collections import deque

from game.core.event import (
    EntityMovedEvent,
    EventType,
    PlayerEnteredZoneEvent,
    PlayerLeftZoneEvent,
    PlayerOutsideZoneEvent,
)
from game.core.event_bus import EventBus
from game.world.world import World


class MoveIntent:
    """A queued request from a client to change position."""

    __slots__ = ("entity_id", "new_x", "new_y")

    def __init__(self, entity_id: str, new_x: float, new_y: float) -> None:
        self.entity_id = entity_id
        self.new_x = new_x
        self.new_y = new_y


class MovementSystem:
    """
    Drains movement intents each tick and applies them.

    Publishes ``EntityMovedEvent`` for every successful move,
    plus zone-transition events when a player crosses a
    zone boundary.

    Parameters
    ----------
    world:
        The world instance that owns entity positions and zones.
    event_bus:
        Hub where movement and zone events are published.
    """

    def __init__(self, world: World, event_bus: EventBus) -> None:
        self._world = world
        self._bus = event_bus
        self._queue: deque[MoveIntent] = deque()

    def enqueue(self, intent: MoveIntent) -> None:
        """Buffer a movement intent for the next tick."""
        self._queue.append(intent)

    def update(self, dt: float) -> None:
        """Process all queued movement intents."""
        while self._queue:
            intent = self._queue.popleft()
            self._process(intent)

    def _process(self, intent: MoveIntent) -> None:
        """Validate and apply a single movement intent."""
        old_pos = self._world.get_entity_position(intent.entity_id)
        if old_pos is None:
            return

        old_x, old_y = old_pos
        result = self._world.move_entity(
            intent.entity_id, intent.new_x, intent.new_y
        )

        self._bus.publish(EntityMovedEvent(
            event_type=EventType.ENTITY_MOVED,
            entity_id=intent.entity_id,
            old_x=old_x, old_y=old_y,
            new_x=intent.new_x, new_y=intent.new_y,
        ))

        if result["entered_zone"]:
            zone = result["entered_zone"]
            self._bus.publish(PlayerEnteredZoneEvent(
                event_type=EventType.PLAYER_ENTERED_ZONE,
                entity_id=intent.entity_id,
                zone_id=zone.zone_id,
                zone_name=zone.name,
            ))

        if result["left_zone"]:
            self._bus.publish(PlayerLeftZoneEvent(
                event_type=EventType.PLAYER_LEFT_ZONE,
                entity_id=intent.entity_id,
                zone_id=result["left_zone"],
            ))

        if result["current_zone_id"] is None:
            self._bus.publish(PlayerOutsideZoneEvent(
                event_type=EventType.PLAYER_OUTSIDE_ZONE,
                entity_id=intent.entity_id,
            ))