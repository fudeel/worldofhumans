# game/network/ws_bridge.py
"""
WebSocket bridge between async WebSocket clients and the game engine.

Subscribes to the shared ``EventBus`` to receive game events,
translates them into WebSocket messages, and delivers them to
connected clients.  Incoming client messages are translated
into game-engine intents (movement, combat, map-object interaction).

This module is entirely self-contained.  Removing it has zero
impact on the rest of the game server.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from typing import Any

from game.characters.character import Character
from game.components.vector2 import Vector2
from game.core.event import (
    EntityDamagedEvent,
    EntityDiedEvent,
    EntityMovedEvent,
    EntitySpawnedEvent,
    EventType,
    GameEvent,
    PlayerEnteredZoneEvent,
)
from game.core.event_bus import EventBus
from game.definitions import CLASS_REGISTRY, get_class_definition
from game.enums.character_class_type import CharacterClassType
from game.enums.faction import Faction
from game.enums.race import Race
from game.network.connection import Connection
from game.network.connection_manager import ConnectionManager
from game.network.ws_protocol import WSMessageType, encode_message
from game.systems.combat_system import AttackIntent, CombatSystem
from game.systems.interaction_system import InteractionSystem
from game.systems.movement_system import MoveIntent, MovementSystem
from game.world.world import World
from game.world.zone_controller import ZoneController

logger = logging.getLogger(__name__)


class WSClient:
    """
    Tracks one connected WebSocket client and its player state.

    Attributes
    ----------
    ws:
        The underlying WebSocket connection object.
    player_id:
        Unique identifier assigned at creation time.
    character:
        The ``Character`` instance once created, or ``None``.
    zone_id:
        The zone the player currently occupies.
    """

    def __init__(self, ws: Any) -> None:
        self.ws = ws
        self.player_id: str = f"player_{uuid.uuid4().hex[:8]}"
        self.character: Character | None = None
        self.zone_id: str | None = None


class WSBridge:
    """
    Manages all WebSocket clients and bridges them to the game engine.

    Holds references to shared game systems but does not own them.
    The bridge subscribes to the ``EventBus`` for outbound events
    and feeds intents into the movement, combat, and interaction
    systems for inbound actions.

    When a character is created, a ``Connection`` is registered in the
    shared ``ConnectionManager`` so that the ``ZoneController`` mob AI
    can detect the player as a valid target.

    Parameters
    ----------
    world:
        Shared world instance.
    event_bus:
        Shared event bus for subscribing to game events.
    connections:
        Shared connection manager — mob AI uses this to identify players.
    movement:
        Movement system to enqueue move intents.
    combat:
        Combat system to enqueue attack intents.
    interaction:
        Interaction system to process map-object interactions.
    controllers:
        Zone controllers keyed by zone id.
    """

    def __init__(
        self,
        world: World,
        event_bus: EventBus,
        connections: ConnectionManager,
        movement: MovementSystem,
        combat: CombatSystem,
        interaction: InteractionSystem,
        controllers: dict[str, ZoneController],
    ) -> None:
        self._world = world
        self._bus = event_bus
        self._conns = connections
        self._movement = movement
        self._combat = combat
        self._interaction = interaction
        self._controllers = controllers
        self._clients: dict[str, WSClient] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

        self._bus.subscribe(EventType.ENTITY_DAMAGED, self._on_entity_damaged)
        self._bus.subscribe(EventType.ENTITY_DIED, self._on_entity_died)
        self._bus.subscribe(EventType.ENTITY_SPAWNED, self._on_entity_spawned)
        self._bus.subscribe(EventType.ENTITY_MOVED, self._on_entity_moved)

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Store the asyncio event loop for scheduling coroutines from threads."""
        self._loop = loop

    # -- client lifecycle ----------------------------------------------------

    def register_client(self, client: WSClient) -> None:
        """Track a newly connected WebSocket client."""
        with self._lock:
            self._clients[client.player_id] = client

    def unregister_client(self, player_id: str) -> None:
        """Remove a disconnected client and clean up its entity and connection."""
        with self._lock:
            client = self._clients.pop(player_id, None)
        if client:
            self._world.remove_entity(player_id)
            self._conns.remove(player_id)

    # -- inbound message handling --------------------------------------------

    def get_class_data(self) -> str:
        """
        Build and return the full class/race/faction data payload.

        Used during character creation to populate the UI.
        """
        factions: dict[str, list[dict]] = {"Alliance": [], "Horde": []}

        for race in Race:
            faction_name = race.faction.value
            available_classes = []
            for ctype, cdef in CLASS_REGISTRY.items():
                if cdef.supports_race(race):
                    available_classes.append({
                        "type": ctype.value,
                        "description": cdef.description,
                        "roles": [r.value for r in cdef.roles],
                        "armor_types": [a.value for a in cdef.armor_types],
                        "weapon_types": [w.value for w in cdef.weapon_types],
                        "talent_trees": list(cdef.talent_trees),
                        "resource_types": [r.value for r in cdef.resource_types],
                    })
            factions[faction_name].append({
                "name": race.value,
                "classes": available_classes,
            })

        zones = []
        for zone in self._world.get_all_zones():
            b = zone.bounds
            zones.append({
                "zone_id": zone.zone_id,
                "name": zone.name,
                "bounds": {
                    "min_x": b.min_x, "min_y": b.min_y,
                    "max_x": b.max_x, "max_y": b.max_y,
                },
            })

        return encode_message(WSMessageType.S_CLASS_DATA, {
            "factions": factions,
            "zones": zones,
        })

    def create_character(
        self, client: WSClient, name: str, race_str: str, class_str: str
    ) -> str:
        """
        Create a character for the client and place it in the world.

        Also registers a ``Connection`` in the shared ``ConnectionManager``
        so that mob AI can detect this player as a valid target.

        Returns the serialised response message.
        """
        try:
            race = Race(race_str)
            class_type = CharacterClassType(class_str)
            class_def = get_class_definition(class_type)
        except (ValueError, KeyError) as exc:
            return encode_message(WSMessageType.S_ERROR, {
                "message": f"Invalid race or class: {exc}",
            })

        if not class_def.supports_race(race):
            return encode_message(WSMessageType.S_ERROR, {
                "message": f"{race.value} cannot be a {class_type.value}.",
            })

        character = Character(
            name=client.player_id,
            race=race,
            class_def=class_def,
            level=1,
            base_health=100,
        )
        client.character = character

        zone = self._world.get_all_zones()[0] if self._world.get_all_zones() else None
        if zone is None:
            return encode_message(WSMessageType.S_ERROR, {
                "message": "No zones available.",
            })

        b = zone.bounds
        center_x = (b.min_x + b.max_x) / 2
        center_y = (b.min_y + b.max_y) / 2

        zone_id = self._world.add_entity(character, center_x, center_y)
        client.zone_id = zone_id

        conn = Connection(client.player_id)
        self._conns.add(conn)

        resources = {}
        for rtype, pool in character.resources.items():
            resources[rtype.value] = {
                "current": pool.current,
                "maximum": pool.maximum,
            }

        return encode_message(WSMessageType.S_CHARACTER_CREATED, {
            "player_id": client.player_id,
            "name": name,
            "race": race.value,
            "class": class_type.value,
            "faction": race.faction.value,
            "level": character.level,
            "health": {
                "current": character.health.current,
                "maximum": character.health.maximum,
            },
            "resources": resources,
            "position": {"x": center_x, "y": center_y},
            "zone_id": zone_id or "",
            "zone_name": zone.name if zone else "",
            "zone_bounds": {
                "min_x": b.min_x, "min_y": b.min_y,
                "max_x": b.max_x, "max_y": b.max_y,
            },
        })

    def handle_move(self, client: WSClient, x: float, y: float) -> None:
        """Enqueue a movement intent for the client's character."""
        if client.character is None:
            return
        self._movement.enqueue(MoveIntent(client.player_id, x, y))

    def handle_attack(self, client: WSClient, target_id: str) -> None:
        """Enqueue an attack intent for the client's character."""
        if client.character is None:
            return
        self._combat.enqueue(AttackIntent(client.player_id, target_id))

    def handle_interact(self, client: WSClient, object_id: str) -> str:
        """
        Process a player's interaction with a map object.

        Validates the player has a character and is in a zone,
        delegates to the ``InteractionSystem``, and returns the
        serialised result message.
        """
        if client.character is None or client.zone_id is None:
            return encode_message(WSMessageType.S_INTERACT_RESULT, {
                "success": False,
                "reason": "No character or not in a zone.",
            })

        ctrl = self._controllers.get(client.zone_id)
        if ctrl is None:
            return encode_message(WSMessageType.S_INTERACT_RESULT, {
                "success": False,
                "reason": "Zone controller not found.",
            })

        result = self._interaction.interact(
            player_id=client.player_id,
            object_id=object_id,
            registry=ctrl.map_objects,
        )

        return encode_message(
            WSMessageType.S_INTERACT_RESULT, result.to_dict()
        )

    # -- world state snapshot ------------------------------------------------

    def build_world_state(self, client: WSClient) -> str | None:
        """
        Build a full snapshot of all entities and map objects visible
        to the client.

        Returns ``None`` if the client has no character or is outside zones.
        """
        if client.character is None or client.zone_id is None:
            return None

        entities: list[dict] = []
        all_in_zone = self._world.get_entities_in_zone(client.zone_id)

        for eid in all_in_zone:
            entity = self._world.get_entity(eid)
            pos = self._world.get_entity_position(eid)
            if entity is None or pos is None:
                continue

            entry: dict[str, Any] = {
                "entity_id": eid,
                "name": entity.name,
                "level": entity.level,
                "health": {
                    "current": entity.health.current,
                    "maximum": entity.health.maximum,
                },
                "position": {"x": pos[0], "y": pos[1]},
                "is_player": eid in self._get_player_ids(),
                "is_self": eid == client.player_id,
                "is_alive": entity.is_alive,
            }

            if isinstance(entity, Character):
                entry["race"] = entity.race.value
                entry["class"] = entity.class_name
                entry["faction"] = entity.faction.value

            ctrl = self._controllers.get(client.zone_id)
            if ctrl and eid in ctrl._mobs:
                mob = ctrl._mobs[eid]
                entry["mob_name"] = mob.display_name
                entry["mob_state"] = mob.state.value
                entry["mob_level"] = mob.entity.level

            entities.append(entry)

        player_pos = self._world.get_entity_position(client.player_id)

        # Include map objects from the zone's registry.
        map_objects: list[dict] = []
        ctrl = self._controllers.get(client.zone_id)
        if ctrl:
            map_objects = ctrl.map_objects.snapshot()

        return encode_message(WSMessageType.S_WORLD_STATE, {
            "zone_id": client.zone_id,
            "entities": entities,
            "map_objects": map_objects,
            "player_position": {
                "x": player_pos[0], "y": player_pos[1],
            } if player_pos else None,
            "player_health": {
                "current": client.character.health.current,
                "maximum": client.character.health.maximum,
            } if client.character else None,
        })

    # -- event subscribers (outbound to WebSocket clients) -------------------

    def _on_entity_damaged(self, event: GameEvent) -> None:
        if not isinstance(event, EntityDamagedEvent):
            return
        msg = encode_message(WSMessageType.S_DAMAGE_DEALT, {
            "target_id": event.entity_id,
            "source_id": event.source_id,
            "amount": event.amount,
            "remaining_health": event.remaining_health,
        })
        self._broadcast_to_zone_clients(event.entity_id, msg)

    def _on_entity_died(self, event: GameEvent) -> None:
        if not isinstance(event, EntityDiedEvent):
            return
        msg = encode_message(WSMessageType.S_ENTITY_DIED, {
            "entity_id": event.entity_id,
            "killer_id": event.killer_id,
            "x": event.position_x,
            "y": event.position_y,
        })
        self._broadcast_to_zone_clients(event.entity_id, msg)

    def _on_entity_spawned(self, event: GameEvent) -> None:
        if not isinstance(event, EntitySpawnedEvent):
            return
        msg = encode_message(WSMessageType.S_ENTITY_SPAWNED, {
            "entity_id": event.entity_id,
            "name": event.entity_name,
            "x": event.position_x,
            "y": event.position_y,
            "zone_id": event.zone_id,
        })
        self._broadcast_to_all(msg)

    def _on_entity_moved(self, event: GameEvent) -> None:
        if not isinstance(event, EntityMovedEvent):
            return
        msg = encode_message(WSMessageType.S_ENTITY_UPDATE, {
            "entity_id": event.entity_id,
            "x": event.new_x,
            "y": event.new_y,
        })
        self._broadcast_to_zone_clients(event.entity_id, msg)

    # -- broadcast helpers ---------------------------------------------------

    def _broadcast_to_zone_clients(self, entity_id: str, msg: str) -> None:
        """Send a message to all clients in the same zone as entity_id."""
        zone_id = self._world.get_entity_zone_id(entity_id)
        if not zone_id:
            return
        with self._lock:
            for client in self._clients.values():
                if client.zone_id == zone_id and client.ws:
                    self._send_async(client.ws, msg)

    def _broadcast_to_all(self, msg: str) -> None:
        """Send a message to all connected clients."""
        with self._lock:
            for client in self._clients.values():
                if client.ws:
                    self._send_async(client.ws, msg)

    def _send_async(self, ws: Any, msg: str) -> None:
        """Schedule a WebSocket send from a synchronous context."""
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._safe_send(ws, msg), self._loop
            )

    @staticmethod
    async def _safe_send(ws: Any, msg: str) -> None:
        """Send a message, silently ignoring closed connections."""
        try:
            await ws.send(msg)
        except Exception:
            pass

    def _get_player_ids(self) -> set[str]:
        """Return all currently connected player ids."""
        with self._lock:
            return {c.player_id for c in self._clients.values()}