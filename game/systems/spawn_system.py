# game/systems/spawn_system.py
"""
Manages mob life cycles: initial spawn and timed respawn.

When a mob dies, its template is placed on a cooldown timer.
Once the timer expires, a fresh mob is spawned at the
template's configured position.
"""

from __future__ import annotations

from game.characters.living_entity import LivingEntity
from game.core.event import (
    EntityDiedEvent,
    EntitySpawnedEvent,
    EventType,
    GameEvent,
)
from game.core.event_bus import EventBus
from game.world.world import World


class _RespawnTimer:
    """Tracks remaining seconds until a mob template respawns."""

    __slots__ = ("template", "remaining")

    def __init__(self, template: dict, delay: float) -> None:
        self.template = template
        self.remaining = delay


class SpawnSystem:
    """
    Spawns mobs from templates and handles respawn after death.

    On construction, call ``register_template`` for each mob
    the zone should contain.  The system will spawn them
    immediately and re-spawn them after they die.

    Parameters
    ----------
    world:
        World instance to place entities into.
    event_bus:
        Subscribes to death events; publishes spawn events.
    """

    def __init__(self, world: World, event_bus: EventBus) -> None:
        self._world = world
        self._bus = event_bus
        self._templates: dict[str, dict] = {}
        self._timers: list[_RespawnTimer] = []

        self._bus.subscribe(EventType.ENTITY_DIED, self._on_entity_died)

    # -- registration --------------------------------------------------------

    def register_template(self, template: dict) -> None:
        """
        Register a mob template and spawn it immediately.

        *template* must contain at minimum: ``id``, ``name``,
        ``base_health``, ``spawn_x``, ``spawn_y``, ``zone_id``,
        ``respawn_sec``.
        """
        self._templates[template["id"]] = template
        self._spawn_from_template(template)

    # -- tick ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Tick down respawn timers and spawn mobs that are ready."""
        still_waiting: list[_RespawnTimer] = []
        for timer in self._timers:
            timer.remaining -= dt
            if timer.remaining <= 0:
                self._spawn_from_template(timer.template)
            else:
                still_waiting.append(timer)
        self._timers = still_waiting

    # -- internal ------------------------------------------------------------

    def _spawn_from_template(self, template: dict) -> None:
        """Create a living entity from a template and place it in the world."""
        entity = LivingEntity(
            name=template["id"],
            max_health=template["base_health"],
            level=template.get("level", 1),
        )
        zone_id = self._world.add_entity(
            entity, template["spawn_x"], template["spawn_y"]
        )
        self._bus.publish(EntitySpawnedEvent(
            event_type=EventType.ENTITY_SPAWNED,
            entity_id=template["id"],
            entity_name=template["name"],
            position_x=template["spawn_x"],
            position_y=template["spawn_y"],
            zone_id=zone_id or "",
        ))

    def _on_entity_died(self, event: GameEvent) -> None:
        """Queue a respawn timer when a registered mob dies."""
        if not isinstance(event, EntityDiedEvent):
            return
        template = self._templates.get(event.entity_id)
        if template is None:
            return
        self._world.remove_entity(event.entity_id)
        self._timers.append(
            _RespawnTimer(template, float(template["respawn_sec"]))
        )