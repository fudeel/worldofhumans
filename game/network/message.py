# game/network/message.py
"""
Network message container with JSON serialisation.

Messages are the unit of communication between client and server.
Each carries a ``MessageType`` and a payload dict.
"""

from __future__ import annotations

import json

from game.network.message_type import MessageType


class Message:
    """
    A single network message.

    Parameters
    ----------
    msg_type:
        What kind of message this is.
    payload:
        Arbitrary data dict carried by the message.
    """

    def __init__(self, msg_type: MessageType, payload: dict | None = None) -> None:
        self._type = msg_type
        self._payload = payload or {}

    @property
    def msg_type(self) -> MessageType:
        return self._type

    @property
    def payload(self) -> dict:
        return self._payload

    # -- serialisation -------------------------------------------------------

    def to_json(self) -> str:
        """Serialise the message to a JSON string."""
        return json.dumps({
            "type": self._type.value,
            "payload": self._payload,
        })

    @classmethod
    def from_json(cls, raw: str) -> "Message":
        """Deserialise a JSON string into a ``Message``."""
        data = json.loads(raw)
        return cls(
            msg_type=MessageType(data["type"]),
            payload=data.get("payload", {}),
        )

    def __repr__(self) -> str:
        return f"Message({self._type.value}, {self._payload})"