# game/network/message_type.py
"""Identifiers for every message the client and server can exchange."""

from enum import Enum


class MessageType(Enum):
    """
    Discriminator for network messages.

    Prefixed ``C_`` for client-to-server, ``S_`` for
    server-to-client.
    """

    # Client → Server
    C_CONNECT = "c_connect"
    C_DISCONNECT = "c_disconnect"
    C_MOVE = "c_move"
    C_ATTACK = "c_attack"
    C_INTERACT = "c_interact"

    # Server → Client
    S_WELCOME = "s_welcome"
    S_CHARACTER_DATA = "s_character_data"
    S_ZONE_ENTERED = "s_zone_entered"
    S_ZONE_LEFT = "s_zone_left"
    S_OUTSIDE_ZONE = "s_outside_zone"
    S_ENTITY_UPDATE = "s_entity_update"
    S_ENTITY_SPAWNED = "s_entity_spawned"
    S_ENTITY_DESPAWNED = "s_entity_despawned"
    S_DAMAGE_DEALT = "s_damage_dealt"
    S_ENTITY_DIED = "s_entity_died"
    S_ENTITY_HEALED = "s_entity_healed"
    S_ERROR = "s_error"