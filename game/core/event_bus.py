# game/core/event_bus.py
"""
Synchronous publish / subscribe hub for game events.

Systems publish events as they mutate state.  Other systems
subscribe to specific ``EventType`` values and react accordingly.
All dispatch happens within the same tick — no threading.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from game.core.event import EventType, GameEvent


class EventBus:
    """
    Central event dispatcher for the game server.

    Subscribers register a callback against one or more
    ``EventType`` values.  When an event of that type is
    published, every matching callback is invoked in
    registration order.
    """

    def __init__(self) -> None:
        self._listeners: dict[EventType, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: EventType, callback: Callable[[GameEvent], None]) -> None:
        """
        Register *callback* to be called whenever *event_type* is published.

        Parameters
        ----------
        event_type:
            The event discriminator to listen for.
        callback:
            A callable accepting a single ``GameEvent`` argument.
        """
        self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """Remove a previously registered callback."""
        listeners = self._listeners.get(event_type)
        if listeners and callback in listeners:
            listeners.remove(callback)

    def publish(self, event: GameEvent) -> None:
        """
        Dispatch *event* to all subscribers of its type.

        Callbacks are invoked synchronously in registration order.
        """
        for callback in self._listeners.get(event.event_type, []):
            callback(event)

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._listeners.clear()