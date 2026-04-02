# game/network/ws_protocol.py
"""
WebSocket protocol definitions for client-server communication.

Defines message types and serialisation helpers used by the
WebSocket bridge. This module is entirely independent of the
existing terminal-based network layer and can be removed
without affecting any other game systems.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any


class WSMessageType(Enum):
    """
    Discriminator for WebSocket messages.

    Prefixed ``C_`` for client-to-server, ``S_`` for server-to-client.
    """

    # Client -> Server
    C_GET_CLASS_DATA = "c_get_class_data"
    C_CREATE_CHARACTER = "c_create_character"
    C_MOVE = "c_move"
    C_ATTACK = "c_attack"
    C_DISCONNECT = "c_disconnect"
    C_LOOT_ITEM = "c_loot_item"
    C_LOOT_MONEY = "c_loot_money"
    C_INTERACT_NPC = "c_interact_npc"
    C_ACCEPT_QUEST = "c_accept_quest"
    C_ABANDON_QUEST = "c_abandon_quest"
    C_TURN_IN_QUEST = "c_turn_in_quest"
    C_GET_INVENTORY = "c_get_inventory"
    C_GET_QUEST_LOG = "c_get_quest_log"
    C_VENDOR_BUY = "c_vendor_buy"
    C_VENDOR_SELL = "c_vendor_sell"

    # Server -> Client
    S_CLASS_DATA = "s_class_data"
    S_CHARACTER_CREATED = "s_character_created"
    S_ZONE_ENTERED = "s_zone_entered"
    S_WORLD_STATE = "s_world_state"
    S_ENTITY_UPDATE = "s_entity_update"
    S_DAMAGE_DEALT = "s_damage_dealt"
    S_ENTITY_DIED = "s_entity_died"
    S_ENTITY_SPAWNED = "s_entity_spawned"
    S_PLAYER_DAMAGED = "s_player_damaged"
    S_LOOT_AVAILABLE = "s_loot_available"
    S_LOOT_RESULT = "s_loot_result"
    S_LOOT_EXPIRED = "s_loot_expired"
    S_NPC_INTERACTION = "s_npc_interaction"
    S_QUEST_OFFERED = "s_quest_offered"
    S_QUEST_ACCEPTED = "s_quest_accepted"
    S_QUEST_UPDATE = "s_quest_update"
    S_QUEST_COMPLETED = "s_quest_completed"
    S_QUEST_TURNED_IN = "s_quest_turned_in"
    S_QUEST_LOG = "s_quest_log"
    S_INVENTORY_UPDATE = "s_inventory_update"
    S_CURRENCY_UPDATE = "s_currency_update"
    S_EXPERIENCE_GAINED = "s_experience_gained"
    S_LEVEL_UP = "s_level_up"
    S_VENDOR_OPEN = "s_vendor_open"
    S_VENDOR_RESULT = "s_vendor_result"
    S_ERROR = "s_error"


def encode_message(msg_type: WSMessageType, payload: dict[str, Any] | None = None) -> str:
    """Serialise a WebSocket message to a JSON string."""
    return json.dumps({
        "type": msg_type.value,
        "payload": payload or {},
    })


def decode_message(raw: str) -> tuple[WSMessageType, dict[str, Any]]:
    """
    Deserialise a JSON string into a message type and payload.

    Raises ``ValueError`` if the message type is unrecognised.
    """
    data = json.loads(raw)
    msg_type = WSMessageType(data["type"])
    payload = data.get("payload", {})
    return msg_type, payload