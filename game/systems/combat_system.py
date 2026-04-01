# game/systems/combat_system.py
"""
Processes attack intents and resolves damage.

Combat is zone-gated: a player must be inside a gaming zone
to deal or receive damage.  Attacks are also range-gated:
the attacker must be within ``attack_range`` world units of
the target.  All hits are validated server-side.
"""

from __future__ import annotations

import math
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
    attack_range:
        Maximum distance in world units between attacker and
        target for a melee hit to connect.
    """

    def __init__(
        self,
        world: World,
        event_bus: EventBus,
        base_damage: int = 10,
        attack_range: float = 15.0,
    ) -> None:
        self._world = world
        self._bus = event_bus
        self._base_damage = base_damage
        self._attack_range = attack_range
        self._queue: deque[AttackIntent] = deque()

    @property
    def attack_range(self) -> float:
        """Maximum melee attack distance in world units."""
        return self._attack_range

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

        # ── Range check ────────────────────────────────────────────
        attacker_pos = self._world.get_entity_position(intent.attacker_id)
        target_pos = self._world.get_entity_position(intent.target_id)
        if attacker_pos is None or target_pos is None:
            return

        dx = attacker_pos[0] - target_pos[0]
        dy = attacker_pos[1] - target_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > self._attack_range:
            return
        # ───────────────────────────────────────────────────────────

        actual = target.take_damage(self._base_damage)

        self._bus.publish(EntityDamagedEvent(
            event_type=EventType.ENTITY_DAMAGED,
            entity_id=intent.target_id,
            source_id=intent.attacker_id,
            amount=actual,
            remaining_health=target.health.current,
        ))

        if not target.is_alive:
            px, py = target_pos
            self._bus.publish(EntityDiedEvent(
                event_type=EventType.ENTITY_DIED,
                entity_id=intent.target_id,
                killer_id=intent.attacker_id,
                position_x=px,
                position_y=py,
            ))