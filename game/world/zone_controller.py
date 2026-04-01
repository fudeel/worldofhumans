# game/world/zone_controller.py
"""
Autonomous controller for a single gaming zone.

Runs in its own thread and drives the zone's life cycle:
mob AI evaluation, movement, combat, respawn timers, map-object
respawns, and event broadcasting — all without manual tick commands.

One ``ZoneController`` per zone. The server holds a dict of
them and starts each when the server boots.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from game.components.vector2 import Vector2
from game.core.event import (
    EntityDamagedEvent,
    EntityDiedEvent,
    EntitySpawnedEvent,
    EventType,
    GameEvent,
)
from game.core.event_bus import EventBus
from game.network.connection_manager import ConnectionManager
from game.network.message import Message
from game.network.message_type import MessageType
from game.systems.combat_system import AttackIntent, CombatSystem
from game.systems.movement_system import MoveIntent, MovementSystem
from game.systems.sync_system import SyncSystem
from game.world.map_object import MapObject
from game.world.map_object_registry import MapObjectRegistry
from game.world.mob_instance import MobInstance
from game.world.world import World
from game.world.zone import Zone


class _RespawnEntry:
    """Tracks a dead mob awaiting respawn."""

    __slots__ = ("mob", "remaining")

    def __init__(self, mob: MobInstance, delay: float) -> None:
        self.mob = mob
        self.remaining = delay


class ZoneController:
    """
    Keeps one gaming zone alive by auto-ticking at a fixed rate.

    Responsibilities each tick:

    1. Evaluate every mob's AI brain → produce move / attack actions.
    2. Feed actions into the movement and combat systems.
    3. Advance respawn timers and re-spawn dead mobs.
    4. Advance map-object respawn timers.
    5. Flush network messages to nearby players.

    Parameters
    ----------
    zone:
        The zone this controller manages.
    world:
        Shared world instance (entity positions, spatial grid).
    event_bus:
        Shared event bus for publishing and subscribing.
    connections:
        Shared connection manager for outbound messages.
    movement:
        Movement system (shared across zones).
    combat:
        Combat system (shared across zones).
    sync:
        Sync system for broadcasting events to clients.
    tick_rate:
        Server ticks per second for this zone.
    """

    def __init__(
        self,
        zone: Zone,
        world: World,
        event_bus: EventBus,
        connections: ConnectionManager,
        movement: MovementSystem,
        combat: CombatSystem,
        sync: SyncSystem,
        tick_rate: int = 20,
    ) -> None:
        self._zone = zone
        self._world = world
        self._bus = event_bus
        self._conns = connections
        self._movement = movement
        self._combat = combat
        self._sync = sync
        self._tick_rate = tick_rate
        self._tick_interval = 1.0 / tick_rate

        self._mobs: dict[str, MobInstance] = {}
        self._respawn_queue: deque[_RespawnEntry] = deque()
        self._map_objects = MapObjectRegistry(zone.zone_id)
        self._running = False
        self._thread: threading.Thread | None = None
        self._tick_count = 0

        self._bus.subscribe(EventType.ENTITY_DAMAGED, self._on_entity_damaged)
        self._bus.subscribe(EventType.ENTITY_DIED, self._on_entity_died)

    # -- public properties ---------------------------------------------------

    @property
    def zone(self) -> Zone:
        """The zone being controlled."""
        return self._zone

    @property
    def tick_count(self) -> int:
        """Total ticks executed since start."""
        return self._tick_count

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def mob_count(self) -> int:
        """Number of live mobs in this zone."""
        return len(self._mobs)

    @property
    def map_objects(self) -> MapObjectRegistry:
        """The zone's map-object registry."""
        return self._map_objects

    # -- mob registration ----------------------------------------------------

    def register_mob(self, mob: MobInstance) -> None:
        """
        Add a mob to this zone and place it in the world.

        The mob is spawned at its template's spawn position.
        """
        self._mobs[mob.mob_id] = mob
        self._world.add_entity(
            mob.entity, mob.spawn_pos.x, mob.spawn_pos.y
        )

    # -- map-object registration ---------------------------------------------

    def register_map_object(self, obj: MapObject) -> None:
        """
        Add a map object to this zone's registry.

        The object is immediately visible to players in the zone.
        """
        self._map_objects.register(obj)

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Start the zone tick loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name=f"zone-{self._zone.zone_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the loop to stop and wait for the thread to exit."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    # -- tick loop -----------------------------------------------------------

    def _loop(self) -> None:
        """Fixed-rate tick loop running in a dedicated thread."""
        while self._running:
            start = time.monotonic()
            self._tick(self._tick_interval)
            elapsed = time.monotonic() - start
            sleep_time = self._tick_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _tick(self, dt: float) -> None:
        """
        Execute one server tick.

        1. Evaluate mob AI → enqueue intents.
        2. Process movement intents.
        3. Process combat intents.
        4. Advance mob respawn timers.
        5. Advance map-object respawn timers.
        6. Flush outbound messages.
        """
        self._evaluate_mob_ai(dt)
        self._movement.update(dt)
        self._combat.update(dt)
        self._process_respawns(dt)
        self._map_objects.update(dt)
        self._sync.update(dt)
        self._tick_count += 1

    # -- mob AI evaluation ---------------------------------------------------

    def _evaluate_mob_ai(self, dt: float) -> None:
        """Run every live mob's brain and enqueue resulting actions."""
        player_ids = self._get_zone_player_ids()
        player_positions = self._get_player_positions(player_ids)

        for mob in list(self._mobs.values()):
            if not mob.is_alive:
                continue

            mob_pos_tuple = self._world.get_entity_position(mob.mob_id)
            if mob_pos_tuple is None:
                continue
            mob_pos = Vector2(mob_pos_tuple[0], mob_pos_tuple[1])

            nearby_players = self._get_nearby_players(mob.mob_id, player_ids)

            action = mob.brain.evaluate(
                mob_pos=mob_pos,
                spawn_pos=mob.spawn_pos,
                nearby_player_ids=nearby_players,
                player_positions=player_positions,
                dt=dt,
            )

            if action["action"] == "move":
                dest = action["move_to"]
                self._movement.enqueue(
                    MoveIntent(mob.mob_id, dest.x, dest.y)
                )
            elif action["action"] == "attack":
                self._combat.enqueue(
                    AttackIntent(mob.mob_id, action["target_id"])
                )

    # -- respawn management --------------------------------------------------

    def _process_respawns(self, dt: float) -> None:
        """Tick down respawn timers and re-spawn ready mobs."""
        still_waiting: deque[_RespawnEntry] = deque()
        for entry in self._respawn_queue:
            entry.remaining -= dt
            if entry.remaining <= 0:
                self._respawn_mob(entry.mob)
            else:
                still_waiting.append(entry)
        self._respawn_queue = still_waiting

    def _respawn_mob(self, mob: MobInstance) -> None:
        """Recreate a dead mob from its template at the spawn point."""
        new_mob = MobInstance.from_template(mob.template)
        self._mobs[new_mob.mob_id] = new_mob
        self._world.add_entity(
            new_mob.entity, new_mob.spawn_pos.x, new_mob.spawn_pos.y
        )
        self._bus.publish(EntitySpawnedEvent(
            event_type=EventType.ENTITY_SPAWNED,
            entity_id=new_mob.mob_id,
            entity_name=new_mob.display_name,
            position_x=new_mob.spawn_pos.x,
            position_y=new_mob.spawn_pos.y,
            zone_id=self._zone.zone_id,
        ))

    # -- event subscribers ---------------------------------------------------

    def _on_entity_damaged(self, event: GameEvent) -> None:
        """When a mob in this zone takes damage, provoke its brain."""
        if not isinstance(event, EntityDamagedEvent):
            return
        mob = self._mobs.get(event.entity_id)
        if mob and mob.is_alive:
            mob.brain.on_provoked(event.source_id)

    def _on_entity_died(self, event: GameEvent) -> None:
        """When a mob in this zone dies, queue it for respawn."""
        if not isinstance(event, EntityDiedEvent):
            return
        mob = self._mobs.get(event.entity_id)
        if mob is None:
            return
        mob.brain.on_died()
        self._world.remove_entity(mob.mob_id)
        del self._mobs[mob.mob_id]
        self._respawn_queue.append(
            _RespawnEntry(mob, mob.respawn_sec)
        )

    # -- helpers -------------------------------------------------------------

    def _get_zone_player_ids(self) -> list[str]:
        """Return player ids currently inside this zone."""
        all_in_zone = self._world.get_entities_in_zone(self._zone.zone_id)
        active_conns = self._conns.get_all_ids()
        return [eid for eid in all_in_zone if eid in active_conns]

    def _get_player_positions(self, player_ids: list[str]) -> dict[str, Vector2]:
        """Build a dict of player id → Vector2 position."""
        positions: dict[str, Vector2] = {}
        for pid in player_ids:
            pos = self._world.get_entity_position(pid)
            if pos:
                positions[pid] = Vector2(pos[0], pos[1])
        return positions

    def _get_nearby_players(self, mob_id: str, all_player_ids: list[str]) -> list[str]:
        """Return player ids near the given mob."""
        nearby = self._world.get_nearby_entity_ids(mob_id)
        return [pid for pid in all_player_ids if pid in nearby]