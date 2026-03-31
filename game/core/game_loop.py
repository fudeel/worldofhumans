# game/core/game_loop.py
"""
Fixed-rate game loop driving the server simulation.

Each tick drains the input queue, updates every registered
system, and sleeps until the next tick is due.  The loop
runs in the main thread — no concurrency within a tick.
"""

from __future__ import annotations

import time
from typing import Protocol


class System(Protocol):
    """Interface every game system must satisfy."""

    def update(self, dt: float) -> None:
        """Advance the system by *dt* seconds."""
        ...


class GameLoop:
    """
    Runs registered systems at a fixed tick rate.

    Parameters
    ----------
    tick_rate:
        Target ticks per second (default 20 → 50 ms per tick).
    """

    def __init__(self, tick_rate: int = 20) -> None:
        self._tick_rate = tick_rate
        self._tick_interval = 1.0 / tick_rate
        self._systems: list[System] = []
        self._running = False
        self._tick_count = 0

    # -- registration --------------------------------------------------------

    def register_system(self, system: System) -> None:
        """Add a system to the update cycle."""
        self._systems.append(system)

    # -- control -------------------------------------------------------------

    @property
    def tick_count(self) -> int:
        """Total ticks executed since the loop started."""
        return self._tick_count

    @property
    def is_running(self) -> bool:
        """``True`` while the loop is actively ticking."""
        return self._running

    def start(self) -> None:
        """
        Begin the tick loop.

        Blocks the calling thread until ``stop()`` is called
        (typically from a signal handler or a system).
        """
        self._running = True
        previous_time = time.monotonic()

        while self._running:
            current_time = time.monotonic()
            dt = current_time - previous_time
            previous_time = current_time

            self._tick(dt)

            elapsed = time.monotonic() - current_time
            sleep_time = self._tick_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self) -> None:
        """Signal the loop to exit after the current tick completes."""
        self._running = False

    def tick_once(self, dt: float) -> None:
        """Execute a single manual tick (useful for testing)."""
        self._tick(dt)

    # -- internal ------------------------------------------------------------

    def _tick(self, dt: float) -> None:
        """Run every registered system once."""
        for system in self._systems:
            system.update(dt)
        self._tick_count += 1