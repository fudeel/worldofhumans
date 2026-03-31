# game/network/connection_manager.py
"""
Registry of every active client connection.

Provides lookup by player id and bulk operations such as
broadcasting a message to a set of connections.
"""

from __future__ import annotations

from game.network.connection import Connection
from game.network.message import Message


class ConnectionManager:
    """
    Owns and indexes all live ``Connection`` instances.

    Used by the sync system to deliver messages to the
    right players.
    """

    def __init__(self) -> None:
        self._connections: dict[str, Connection] = {}

    # -- lifecycle -----------------------------------------------------------

    def add(self, connection: Connection) -> None:
        """Register a new connection."""
        self._connections[connection.connection_id] = connection

    def remove(self, connection_id: str) -> Connection | None:
        """
        Close and unregister a connection.

        Returns the removed ``Connection``, or ``None`` if not found.
        """
        conn = self._connections.pop(connection_id, None)
        if conn:
            conn.close()
        return conn

    def get(self, connection_id: str) -> Connection | None:
        """Look up a connection by player id."""
        return self._connections.get(connection_id)

    # -- delivery ------------------------------------------------------------

    def send_to(self, connection_id: str, message: Message) -> None:
        """Queue a message for a single player."""
        conn = self._connections.get(connection_id)
        if conn and conn.is_active:
            conn.send(message)

    def send_to_many(self, connection_ids: set[str], message: Message) -> None:
        """Queue the same message for multiple players."""
        for cid in connection_ids:
            self.send_to(cid, message)

    def broadcast_all(self, message: Message) -> None:
        """Queue a message for every connected player."""
        for conn in self._connections.values():
            if conn.is_active:
                conn.send(message)

    # -- queries -------------------------------------------------------------

    @property
    def active_count(self) -> int:
        """Number of currently active connections."""
        return sum(1 for c in self._connections.values() if c.is_active)

    def get_all_ids(self) -> set[str]:
        """Return ids of all active connections."""
        return {cid for cid, c in self._connections.items() if c.is_active}