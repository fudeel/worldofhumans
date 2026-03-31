# game/components/vector2.py
"""Minimal 2D vector for position and movement calculations."""

from __future__ import annotations

import math


class Vector2:
    """
    A 2D point or direction used for world positions.

    Intentionally lightweight — no operator overloads beyond
    what the game loop actually needs.

    Parameters
    ----------
    x:
        Horizontal coordinate.
    y:
        Vertical coordinate.
    """

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y

    def distance_to(self, other: "Vector2") -> float:
        """Euclidean distance between this point and *other*."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def move_toward(self, target: "Vector2", max_step: float) -> "Vector2":
        """
        Return a new point moved from here toward *target*
        by at most *max_step* units.

        If the distance is less than *max_step*, returns
        the target position exactly.
        """
        dist = self.distance_to(target)
        if dist <= max_step or dist == 0:
            return Vector2(target.x, target.y)
        ratio = max_step / dist
        return Vector2(
            self.x + (target.x - self.x) * ratio,
            self.y + (target.y - self.y) * ratio,
        )

    def copy(self) -> "Vector2":
        """Return an independent copy."""
        return Vector2(self.x, self.y)

    def __repr__(self) -> str:
        return f"Vector2({self.x:.1f}, {self.y:.1f})"