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
    C_INTERACT = "c_interact"
    C_DISCONNECT = "c_disconnect"

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
    S_INTERACT_RESULT = "s_interact_result"
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