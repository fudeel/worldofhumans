# game/network/ws_bridge.py
"""
WebSocket bridge between async WebSocket clients and the game engine.

Subscribes to the shared ``EventBus`` to receive game events,
translates them into WebSocket messages, and delivers them to
connected clients.  Incoming client messages are translated
into game-engine intents (movement, combat, loot, quests,
vendor interactions, and experience).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
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
    ExperienceGainedEvent,
    GameEvent,
    LevelUpEvent,
    LootDroppedEvent,
    LootExpiredEvent,
    QuestCompletedEvent,
)
from game.core.event_bus import EventBus
from game.definitions import CLASS_REGISTRY, get_class_definition
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.network.connection import Connection
from game.network.connection_manager import ConnectionManager
from game.network.ws_protocol import WSMessageType, encode_message
from game.systems.combat_system import AttackIntent, CombatSystem
from game.systems.experience_system import ExperienceSystem
from game.systems.loot_system import LootSystem
from game.systems.movement_system import MoveIntent, MovementSystem
from game.systems.quest_system import QuestSystem
from game.systems.vendor_system import VendorSystem
from game.world.world import World
from game.world.zone_controller import ZoneController

logger = logging.getLogger(__name__)

_LOOT_RANGE = 40.0
"""Maximum distance (world units) a player can be from a loot drop to pick it up."""

_NPC_INTERACT_RANGE = 50.0
"""Maximum distance to interact with an NPC quest giver or vendor."""


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

    Parameters
    ----------
    world:
        Shared world instance.
    event_bus:
        Shared event bus for subscribing to game events.
    connections:
        Shared connection manager.
    movement:
        Movement system to enqueue move intents.
    combat:
        Combat system to enqueue attack intents.
    controllers:
        Zone controllers keyed by zone id.
    loot_system:
        Loot drop manager.
    quest_system:
        Quest catalogue and interaction handler.
    vendor_system:
        Vendor inventory and transaction handler.
    """

    def __init__(
            self,
            world: World,
            event_bus: EventBus,
            connections: ConnectionManager,
            movement: MovementSystem,
            combat: CombatSystem,
            controllers: dict[str, ZoneController],
            loot_system: LootSystem,
            quest_system: QuestSystem,
            vendor_system: VendorSystem,
    ) -> None:
        self._world = world
        self._bus = event_bus
        self._conns = connections
        self._movement = movement
        self._combat = combat
        self._controllers = controllers
        self._loot = loot_system
        self._quests = quest_system
        self._vendors = vendor_system
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

    # -- class data ----------------------------------------------------------

    def get_class_data(self) -> str:
        """Build and return the full class/race/faction data payload."""
        factions: dict[str, list] = {"Alliance": [], "Horde": []}

        for race in Race:
            race_classes = []
            for ctype in CharacterClassType:
                cdef = get_class_definition(ctype)
                if cdef.supports_race(race):
                    race_classes.append({
                        "type": ctype.value,
                        "description": cdef.description,
                        "roles": [r.value for r in cdef.roles],
                        "armor_types": [a.value for a in cdef.armor_types],
                        "weapon_types": [w.value for w in cdef.weapon_types],
                        "talent_trees": list(cdef.talent_trees),
                        "resource_types": [r.value for r in cdef.resource_types],
                    })
            if race_classes:
                factions[race.faction.value].append({
                    "name": race.value,
                    "classes": race_classes,
                })

        zones = []
        for z in self._world.get_all_zones():
            zones.append({
                "zone_id": z.zone_id,
                "name": z.name,
                "bounds": {
                    "min_x": z.bounds.min_x, "min_y": z.bounds.min_y,
                    "max_x": z.bounds.max_x, "max_y": z.bounds.max_y,
                },
            })

        return encode_message(WSMessageType.S_CLASS_DATA, {
            "factions": factions,
            "zones": zones,
        })

    # -- character creation --------------------------------------------------

    def create_character(
            self,
            client: WSClient,
            name: str,
            race_str: str,
            class_str: str,
    ) -> str:
        """Create a character for the given client."""
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
            "inventory": character.inventory.to_dict(),
            "currency": character.currency.to_dict(),
            "quest_log": character.quest_log.to_dict(),
            "experience": character.experience.to_dict(),
        })

    # -- movement & combat ---------------------------------------------------

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

    # -- loot handlers -------------------------------------------------------

    def handle_loot_item(self, client: WSClient, drop_id: str, item_id: str) -> str:
        """
        Player picks up a specific item from a loot drop.

        Validates range, drop existence, and inventory space.
        """
        if client.character is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "No character."})

        drop = self._loot.get_drop(drop_id)
        if drop is None or not drop.is_active:
            return encode_message(WSMessageType.S_LOOT_RESULT, {
                "success": False, "reason": "Loot is no longer available.",
            })

        player_pos = self._world.get_entity_position(client.player_id)
        if player_pos is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "Position unknown."})

        dx = player_pos[0] - drop.position[0]
        dy = player_pos[1] - drop.position[1]
        if (dx * dx + dy * dy) > _LOOT_RANGE * _LOOT_RANGE:
            return encode_message(WSMessageType.S_LOOT_RESULT, {
                "success": False, "reason": "Too far away to loot.",
            })

        if client.character.inventory.is_full:
            return encode_message(WSMessageType.S_LOOT_RESULT, {
                "success": False, "reason": "Inventory is full.",
            })

        item = drop.take_item(item_id)
        if item is None:
            return encode_message(WSMessageType.S_LOOT_RESULT, {
                "success": False, "reason": "Item not found in loot.",
            })

        leftover = client.character.inventory.add_item(item)
        if leftover > 0:
            return encode_message(WSMessageType.S_LOOT_RESULT, {
                "success": False, "reason": "Not enough bag space.",
            })

        self._loot.remove_empty_drops()

        return encode_message(WSMessageType.S_LOOT_RESULT, {
            "success": True,
            "item": item.to_dict(),
            "inventory": client.character.inventory.to_dict(),
            "currency": client.character.currency.to_dict(),
            "drop": drop.to_dict() if drop.is_active and not drop.is_empty else None,
        })

    def handle_loot_money(self, client: WSClient, drop_id: str) -> str:
        """Player picks up money from a loot drop."""
        if client.character is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "No character."})

        drop = self._loot.get_drop(drop_id)
        if drop is None or not drop.is_active:
            return encode_message(WSMessageType.S_LOOT_RESULT, {
                "success": False, "reason": "Loot is no longer available.",
            })

        player_pos = self._world.get_entity_position(client.player_id)
        if player_pos is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "Position unknown."})

        dx = player_pos[0] - drop.position[0]
        dy = player_pos[1] - drop.position[1]
        if (dx * dx + dy * dy) > _LOOT_RANGE * _LOOT_RANGE:
            return encode_message(WSMessageType.S_LOOT_RESULT, {
                "success": False, "reason": "Too far away to loot.",
            })

        money = drop.take_money()
        if money > 0:
            client.character.currency.add(money)

        self._loot.remove_empty_drops()

        return encode_message(WSMessageType.S_LOOT_RESULT, {
            "success": True,
            "money_looted": money,
            "inventory": client.character.inventory.to_dict(),
            "currency": client.character.currency.to_dict(),
            "drop": drop.to_dict() if drop.is_active and not drop.is_empty else None,
        })

    # -- NPC / quest handlers ------------------------------------------------

    def handle_interact_npc(self, client: WSClient, entity_id: str) -> str:
        """
        Player interacts with an NPC (quest giver or vendor).

        If the NPC is a vendor, returns the vendor inventory.
        If the NPC is a quest giver, returns available quests.
        Both roles can coexist on a single NPC.
        """
        if client.character is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "No character."})

        player_pos = self._world.get_entity_position(client.player_id)
        npc_pos = self._world.get_entity_position(entity_id)
        if player_pos is None or npc_pos is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "Position unknown."})

        dx = player_pos[0] - npc_pos[0]
        dy = player_pos[1] - npc_pos[1]
        if (dx * dx + dy * dy) > _NPC_INTERACT_RANGE * _NPC_INTERACT_RANGE:
            return encode_message(WSMessageType.S_NPC_INTERACTION, {
                "success": False, "reason": "Too far away to talk.",
            })

        # Check if NPC is a vendor
        vendor = self._vendors.get_vendor(entity_id)
        if vendor is not None:
            return encode_message(WSMessageType.S_VENDOR_OPEN, {
                "vendor_id": entity_id,
                "vendor": vendor.to_dict(),
                "inventory": client.character.inventory.to_dict(),
                "currency": client.character.currency.to_dict(),
            })

        # Otherwise treat as quest giver
        available = self._quests.get_available_quests_for(entity_id, client.character)
        return encode_message(WSMessageType.S_QUEST_OFFERED, {
            "npc_id": entity_id,
            "quests": [q.to_dict() for q in available],
        })

    # -- vendor handlers -----------------------------------------------------

    def handle_vendor_buy(self, client: WSClient, vendor_id: str, item_id: str) -> str:
        """
        Player purchases one unit of an item from a vendor.

        Validates range, funds, and bag space before executing.
        """
        if client.character is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "No character."})

        player_pos = self._world.get_entity_position(client.player_id)
        npc_pos = self._world.get_entity_position(vendor_id)
        if player_pos is None or npc_pos is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "Position unknown."})

        dx = player_pos[0] - npc_pos[0]
        dy = player_pos[1] - npc_pos[1]
        if (dx * dx + dy * dy) > _NPC_INTERACT_RANGE * _NPC_INTERACT_RANGE:
            return encode_message(WSMessageType.S_VENDOR_RESULT, {
                "success": False, "reason": "Too far away.",
            })

        result = self._vendors.buy_from_vendor(
            vendor_id, item_id,
            client.character.currency,
            client.character.inventory,
        )

        vendor = self._vendors.get_vendor(vendor_id)
        return encode_message(WSMessageType.S_VENDOR_RESULT, {
            "success": result.success,
            "reason": result.reason,
            "action": "buy",
            "vendor": vendor.to_dict() if vendor else None,
            "inventory": client.character.inventory.to_dict(),
            "currency": client.character.currency.to_dict(),
        })

    def handle_vendor_sell(self, client: WSClient, vendor_id: str, slot_index: int) -> str:
        """
        Player sells one unit from an inventory slot to a vendor.

        The vendor pays the item's ``sell_value``.
        """
        if client.character is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "No character."})

        player_pos = self._world.get_entity_position(client.player_id)
        npc_pos = self._world.get_entity_position(vendor_id)
        if player_pos is None or npc_pos is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "Position unknown."})

        dx = player_pos[0] - npc_pos[0]
        dy = player_pos[1] - npc_pos[1]
        if (dx * dx + dy * dy) > _NPC_INTERACT_RANGE * _NPC_INTERACT_RANGE:
            return encode_message(WSMessageType.S_VENDOR_RESULT, {
                "success": False, "reason": "Too far away.",
            })

        result = self._vendors.sell_to_vendor(
            vendor_id, slot_index,
            client.character.currency,
            client.character.inventory,
        )

        vendor = self._vendors.get_vendor(vendor_id)
        return encode_message(WSMessageType.S_VENDOR_RESULT, {
            "success": result.success,
            "reason": result.reason,
            "action": "sell",
            "vendor": vendor.to_dict() if vendor else None,
            "inventory": client.character.inventory.to_dict(),
            "currency": client.character.currency.to_dict(),
        })

    # -- quest handlers ------------------------------------------------------

    def handle_accept_quest(self, client: WSClient, quest_id: str) -> str:
        """Player accepts a quest."""
        if client.character is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "No character."})

        entry = self._quests.accept_quest(client.character, quest_id)
        if entry is None:
            return encode_message(WSMessageType.S_ERROR, {
                "message": "Cannot accept quest (log full, already tracking, or level too low).",
            })

        return encode_message(WSMessageType.S_QUEST_ACCEPTED, {
            "quest": entry.to_dict(),
            "quest_log": client.character.quest_log.to_dict(),
        })

    def handle_abandon_quest(self, client: WSClient, quest_id: str) -> str:
        """Player abandons a quest."""
        if client.character is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "No character."})

        entry = self._quests.abandon_quest(client.character, quest_id)
        if entry is None:
            return encode_message(WSMessageType.S_ERROR, {
                "message": "Quest not found in your log.",
            })

        return encode_message(WSMessageType.S_QUEST_LOG, {
            "quest_log": client.character.quest_log.to_dict(),
        })

    def handle_turn_in_quest(self, client: WSClient, quest_id: str) -> str:
        """Player turns in a completed quest and receives rewards."""
        if client.character is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "No character."})

        entry = self._quests.turn_in_quest(client.character, quest_id)
        if entry is None:
            return encode_message(WSMessageType.S_ERROR, {
                "message": "Quest not completed or not found.",
            })

        # Award quest XP
        exp_result = ExperienceSystem.award_quest_exp(
            client.character.experience,
            entry.definition.reward.experience,
        )
        if exp_result:
            exp_msg = encode_message(WSMessageType.S_EXPERIENCE_GAINED, {
                "source": "quest",
                "quest_title": entry.definition.title,
                "exp_gained": exp_result.exp_gained,
                "experience": exp_result.tracker_snapshot,
            })
            self._send_async(client.ws, exp_msg)
            if exp_result.level_up:
                lvl_msg = encode_message(WSMessageType.S_LEVEL_UP, {
                    "old_level": exp_result.level_up.old_level,
                    "new_level": exp_result.level_up.new_level,
                    "levels_gained": exp_result.level_up.levels_gained,
                    "experience": exp_result.tracker_snapshot,
                })
                self._send_async(client.ws, lvl_msg)

        return encode_message(WSMessageType.S_QUEST_TURNED_IN, {
            "quest_id": quest_id,
            "reward": entry.definition.reward.to_dict(),
            "quest_log": client.character.quest_log.to_dict(),
            "inventory": client.character.inventory.to_dict(),
            "currency": client.character.currency.to_dict(),
            "experience": client.character.experience.to_dict(),
        })

    def handle_get_inventory(self, client: WSClient) -> str:
        """Return the player's current inventory state."""
        if client.character is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "No character."})

        return encode_message(WSMessageType.S_INVENTORY_UPDATE, {
            "inventory": client.character.inventory.to_dict(),
            "currency": client.character.currency.to_dict(),
        })

    def handle_get_quest_log(self, client: WSClient) -> str:
        """Return the player's current quest log."""
        if client.character is None:
            return encode_message(WSMessageType.S_ERROR, {"message": "No character."})

        return encode_message(WSMessageType.S_QUEST_LOG, {
            "quest_log": client.character.quest_log.to_dict(),
        })

    # -- world state snapshot ------------------------------------------------

    def build_world_state(self, client: WSClient) -> str | None:
        """Build a full snapshot of all entities visible to the client."""
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
                entry["is_quest_giver"] = bool(
                    mob.template.get("is_quest_giver", False)
                )
                entry["is_vendor"] = bool(
                    mob.template.get("is_vendor", False)
                )

            entities.append(entry)

        player_pos = self._world.get_entity_position(client.player_id)

        loot_drops = [d.to_dict() for d in self._loot.get_all_active_drops()]

        return encode_message(WSMessageType.S_WORLD_STATE, {
            "zone_id": client.zone_id,
            "entities": entities,
            "map_objects": [],
            "loot_drops": loot_drops,
            "player_position": {
                "x": player_pos[0], "y": player_pos[1],
            } if player_pos else None,
            "player_health": {
                "current": client.character.health.current,
                "maximum": client.character.health.maximum,
            } if client.character else None,
            "currency": client.character.currency.to_dict(),
            "experience": client.character.experience.to_dict(),
        })

    # -- event subscribers ---------------------------------------------------

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

        # Generate loot drop for the dead mob
        drop = self._loot.generate_drop(
            mob_id=event.entity_id,
            position_x=event.position_x,
            position_y=event.position_y,
        )

        msg = encode_message(WSMessageType.S_ENTITY_DIED, {
            "entity_id": event.entity_id,
            "killer_id": event.killer_id,
            "x": event.position_x,
            "y": event.position_y,
            "loot_drop": drop.to_dict() if drop else None,
        })
        self._broadcast_to_zone_clients(event.entity_id, msg)

        # Determine the victim's level for experience calculation
        victim_level = self._resolve_victim_level(event.entity_id)

        # Award kill XP to the killer (works for both players and mobs)
        self._award_kill_experience(event.killer_id, victim_level)

        # Advance kill-quest objectives for the killer
        killer_client = self._clients.get(event.killer_id)
        if killer_client and killer_client.character:
            updated = self._quests.on_mob_killed(
                killer_client.character, event.entity_id
            )
            if updated:
                for qe in updated:
                    self._send_async(killer_client.ws, encode_message(
                        WSMessageType.S_QUEST_UPDATE, {"quest": qe.to_dict()}
                    ))
                    if qe.is_complete:
                        self._send_async(killer_client.ws, encode_message(
                            WSMessageType.S_QUEST_COMPLETED, {
                                "quest_id": qe.quest_id,
                                "title": qe.definition.title,
                            }
                        ))

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

    # -- experience helpers --------------------------------------------------

    def _resolve_victim_level(self, entity_id: str) -> int:
        """Look up the level of a recently killed entity."""
        for ctrl in self._controllers.values():
            if entity_id in ctrl._mobs:
                return ctrl._mobs[entity_id].entity.level
        entity = self._world.get_entity(entity_id)
        if entity:
            return entity.level
        return 1

    def _award_kill_experience(self, killer_id: str, victim_level: int) -> None:
        """
        Award kill experience to the killer entity.

        Works for player-kills-mob, mob-kills-player, and
        player-kills-player scenarios.
        """
        # Check if killer is a player
        killer_client = self._clients.get(killer_id)
        if killer_client and killer_client.character:
            tracker = killer_client.character.experience
            result = ExperienceSystem.award_kill_exp(tracker, victim_level)
            if result:
                exp_msg = encode_message(WSMessageType.S_EXPERIENCE_GAINED, {
                    "source": "kill",
                    "exp_gained": result.exp_gained,
                    "experience": result.tracker_snapshot,
                })
                self._send_async(killer_client.ws, exp_msg)
                if result.level_up:
                    lvl_msg = encode_message(WSMessageType.S_LEVEL_UP, {
                        "old_level": result.level_up.old_level,
                        "new_level": result.level_up.new_level,
                        "levels_gained": result.level_up.levels_gained,
                        "experience": result.tracker_snapshot,
                    })
                    self._send_async(killer_client.ws, lvl_msg)
            return

        # Killer is a mob — award XP to the mob's entity tracker
        for ctrl in self._controllers.values():
            mob = ctrl._mobs.get(killer_id)
            if mob is not None:
                ExperienceSystem.award_kill_exp(
                    mob.entity.experience, victim_level
                )
                return

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