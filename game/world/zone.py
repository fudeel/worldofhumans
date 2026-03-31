# game/world/zone.py
"""
A gaming zone — a bounded rectangular area of the world
where gameplay is active.

Players outside all zones receive no world data.  Only
once they step inside a zone boundary does the server
begin streaming entity updates to them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ZoneBounds:
    """Axis-aligned rectangle defining a zone's boundary."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def contains(self, x: float, y: float) -> bool:
        """Return ``True`` if the point (x, y) is inside this rectangle."""
        return (self.min_x <= x <= self.max_x and
                self.min_y <= y <= self.max_y)

    @property
    def width(self) -> float:
        """Horizontal span of the zone."""
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        """Vertical span of the zone."""
        return self.max_y - self.min_y


class Zone:
    """
    A discrete gaming area within the world.

    Entities inside a zone are tracked by the zone's spatial
    grid and broadcast to nearby players.  Entities outside
    are invisible to the server's streaming systems.

    Parameters
    ----------
    zone_id:
        Unique identifier.
    name:
        Human-readable zone name.
    bounds:
        Rectangular boundary of the zone.
    chunk_size:
        Side length of each spatial grid cell.
    """

    def __init__(
        self,
        zone_id: str,
        name: str,
        bounds: ZoneBounds,
        chunk_size: int = 100,
    ) -> None:
        self._id = zone_id
        self._name = name
        self._bounds = bounds
        self._chunk_size = chunk_size

    @property
    def zone_id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def bounds(self) -> ZoneBounds:
        return self._bounds

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    def contains(self, x: float, y: float) -> bool:
        """Check whether a world position falls inside this zone."""
        return self._bounds.contains(x, y)

    def __repr__(self) -> str:
        return f"Zone('{self._id}', '{self._name}')"