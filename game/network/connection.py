# game/network/connection.py
"""
A single client session.

Wraps the transport layer (terminal I/O for now) and
associates it with a player id.  When the transport is
replaced with WebSockets later, only this file changes.
"""

from __future__ import annotations

from collections import deque

from game.network.message import Message


class Connection:
    """
    Represents one connected client.

    Outbound messages are buffered in a queue and flushed
    by the sync system at the end of each tick.

    Parameters
    ----------
    connection_id:
        Unique session identifier (matches player id).
    """

    def __init__(self, connection_id: str) -> None:
        self._id = connection_id
        self._outbox: deque[Message] = deque()
        self._active = True

    @property
    def connection_id(self) -> str:
        return self._id

    @property
    def is_active(self) -> bool:
        """``True`` while the session has not been closed."""
        return self._active

    # -- outbound ------------------------------------------------------------

    def send(self, message: Message) -> None:
        """Queue a message for delivery to this client."""
        if self._active:
            self._outbox.append(message)

    def flush(self) -> list[Message]:
        """
        Drain and return all queued outbound messages.

        Called once per tick by the sync system to batch-deliver.
        """
        messages = list(self._outbox)
        self._outbox.clear()
        return messages

    # -- lifecycle -----------------------------------------------------------

    def close(self) -> None:
        """Mark the session as inactive."""
        self._active = False
        self._outbox.clear()

    def __repr__(self) -> str:
        status = "active" if self._active else "closed"
        return f"Connection('{self._id}', {status})"