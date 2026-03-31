# game/systems/sync_system.py
"""
Translates game events into network messages and delivers
them to the appropriate players.

Zone-gate rule: only players inside a gaming zone receive
world updates.  Players outside get nothing except their
own character data and zone-status messages.
"""

from __future__ import annotations

from game.core.event import (
    EntityDamagedEvent,
    EntityDiedEvent,
    EntityMovedEvent,
    EntitySpawnedEvent,
    EventType,
    GameEvent,
    PlayerEnteredZoneEvent,
    PlayerLeftZoneEvent,
    PlayerOutsideZoneEvent,
)
from game.core.event_bus import EventBus
from game.network.connection_manager import ConnectionManager
from game.network.message import Message
from game.network.message_type import MessageType
from game.world.world import World


class SyncSystem:
    """
    Subscribes to all game events and routes messages to clients.

    For zone-internal events (movement, damage, death, spawn)
    messages are sent only to players whose chunks overlap the
    event origin — the spatial grid's area-of-interest query.

    Parameters
    ----------
    world:
        Provides spatial queries and zone membership.
    event_bus:
        Source of game events.
    connections:
        Destination for outbound client messages.
    """

    def __init__(
        self,
        world: World,
        event_bus: EventBus,
        connections: ConnectionManager,
    ) -> None:
        self._world = world
        self._bus = event_bus
        self._conns = connections

        self._bus.subscribe(EventType.ENTITY_MOVED, self._on_moved)
        self._bus.subscribe(EventType.ENTITY_DAMAGED, self._on_damaged)
        self._bus.subscribe(EventType.ENTITY_DIED, self._on_died)
        self._bus.subscribe(EventType.ENTITY_SPAWNED, self._on_spawned)
        self._bus.subscribe(EventType.PLAYER_ENTERED_ZONE, self._on_entered_zone)
        self._bus.subscribe(EventType.PLAYER_LEFT_ZONE, self._on_left_zone)
        self._bus.subscribe(EventType.PLAYER_OUTSIDE_ZONE, self._on_outside_zone)

    def update(self, dt: float) -> None:
        """Flush all connection outboxes (called once per tick)."""
        for cid in self._conns.get_all_ids():
            conn = self._conns.get(cid)
            if conn:
                for msg in conn.flush():
                    print(f"  >> [{cid}] {msg.msg_type.value}: {msg.payload}")

    # -- event handlers (zone-gated broadcasting) ----------------------------

    def _on_moved(self, event: GameEvent) -> None:
        if not isinstance(event, EntityMovedEvent):
            return
        nearby = self._world.get_nearby_entity_ids(event.entity_id)
        player_ids = nearby & self._conns.get_all_ids()
        msg = Message(MessageType.S_ENTITY_UPDATE, {
            "entity_id": event.entity_id,
            "x": event.new_x,
            "y": event.new_y,
        })
        self._conns.send_to_many(player_ids, msg)

    def _on_damaged(self, event: GameEvent) -> None:
        if not isinstance(event, EntityDamagedEvent):
            return
        nearby = self._world.get_nearby_entity_ids(event.entity_id)
        player_ids = nearby & self._conns.get_all_ids()
        msg = Message(MessageType.S_DAMAGE_DEALT, {
            "target_id": event.entity_id,
            "source_id": event.source_id,
            "amount": event.amount,
            "remaining_health": event.remaining_health,
        })
        self._conns.send_to_many(player_ids, msg)

    def _on_died(self, event: GameEvent) -> None:
        if not isinstance(event, EntityDiedEvent):
            return
        nearby = self._world.get_nearby_entity_ids(event.entity_id)
        player_ids = nearby & self._conns.get_all_ids()
        msg = Message(MessageType.S_ENTITY_DIED, {
            "entity_id": event.entity_id,
            "killer_id": event.killer_id,
            "x": event.position_x,
            "y": event.position_y,
        })
        self._conns.send_to_many(player_ids, msg)

    def _on_spawned(self, event: GameEvent) -> None:
        if not isinstance(event, EntitySpawnedEvent):
            return
        nearby = self._world.get_nearby_entity_ids(event.entity_id)
        player_ids = nearby & self._conns.get_all_ids()
        msg = Message(MessageType.S_ENTITY_SPAWNED, {
            "entity_id": event.entity_id,
            "name": event.entity_name,
            "x": event.position_x,
            "y": event.position_y,
        })
        self._conns.send_to_many(player_ids, msg)

    def _on_entered_zone(self, event: GameEvent) -> None:
        if not isinstance(event, PlayerEnteredZoneEvent):
            return
        self._conns.send_to(event.entity_id, Message(
            MessageType.S_ZONE_ENTERED, {
                "zone_id": event.zone_id,
                "zone_name": event.zone_name,
            }
        ))

    def _on_left_zone(self, event: GameEvent) -> None:
        if not isinstance(event, PlayerLeftZoneEvent):
            return
        self._conns.send_to(event.entity_id, Message(
            MessageType.S_ZONE_LEFT, {"zone_id": event.zone_id}
        ))

    def _on_outside_zone(self, event: GameEvent) -> None:
        if not isinstance(event, PlayerOutsideZoneEvent):
            return
        self._conns.send_to(event.entity_id, Message(
            MessageType.S_OUTSIDE_ZONE, {
                "message": "You are outside the gaming zone.",
            }
        ))