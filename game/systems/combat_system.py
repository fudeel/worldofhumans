# game/systems/combat_system.py
"""
Processes attack intents and resolves damage.

Combat is zone-gated: a player must be inside a gaming zone
to deal or receive damage.  All hits are validated server-side.
"""

from __future__ import annotations

from collections import deque

from game.core.event import (
    EntityDamagedEvent,
    EntityDiedEvent,
    EventType,
    PlayerOutsideZoneEvent,
)
from game.core.event_bus import EventBus
from game.world.world import World


class AttackIntent:
    """A queued request from a client to attack a target."""

    __slots__ = ("attacker_id", "target_id")

    def __init__(self, attacker_id: str, target_id: str) -> None:
        self.attacker_id = attacker_id
        self.target_id = target_id


class CombatSystem:
    """
    Resolves attacks each tick.

    For now damage is a fixed value; the stat-based formula
    will be added when equipment and abilities are implemented.

    Parameters
    ----------
    world:
        Provides entity lookups and zone checks.
    event_bus:
        Publishes damage and death events.
    base_damage:
        Flat damage dealt per successful attack.
    """

    def __init__(
        self, world: World, event_bus: EventBus, base_damage: int = 10
    ) -> None:
        self._world = world
        self._bus = event_bus
        self._base_damage = base_damage
        self._queue: deque[AttackIntent] = deque()

    def enqueue(self, intent: AttackIntent) -> None:
        """Buffer an attack intent for the next tick."""
        self._queue.append(intent)

    def update(self, dt: float) -> None:
        """Resolve all queued attacks."""
        while self._queue:
            intent = self._queue.popleft()
            self._process(intent)

    def _process(self, intent: AttackIntent) -> None:
        """Validate and resolve a single attack."""
        if not self._world.is_entity_in_zone(intent.attacker_id):
            self._bus.publish(PlayerOutsideZoneEvent(
                event_type=EventType.PLAYER_OUTSIDE_ZONE,
                entity_id=intent.attacker_id,
            ))
            return

        target = self._world.get_entity(intent.target_id)
        if target is None or not target.is_alive:
            return

        if not self._world.is_entity_in_zone(intent.target_id):
            return

        actual = target.take_damage(self._base_damage)

        self._bus.publish(EntityDamagedEvent(
            event_type=EventType.ENTITY_DAMAGED,
            entity_id=intent.target_id,
            source_id=intent.attacker_id,
            amount=actual,
            remaining_health=target.health.current,
        ))

        if not target.is_alive:
            pos = self._world.get_entity_position(intent.target_id)
            px, py = pos if pos else (0.0, 0.0)
            self._bus.publish(EntityDiedEvent(
                event_type=EventType.ENTITY_DIED,
                entity_id=intent.target_id,
                killer_id=intent.attacker_id,
                position_x=px,
                position_y=py,
            ))