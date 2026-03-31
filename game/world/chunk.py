# game/world/chunk.py
"""
A single cell in the spatial grid.

Chunks track which entity ids currently occupy them so the
server can quickly answer "who is near this position?" without
iterating every entity in the world.
"""

from __future__ import annotations


class Chunk:
    """
    One square cell in the spatial grid.

    Parameters
    ----------
    chunk_x:
        Column index in the grid.
    chunk_y:
        Row index in the grid.
    """

    def __init__(self, chunk_x: int, chunk_y: int) -> None:
        self._x = chunk_x
        self._y = chunk_y
        self._entity_ids: set[str] = set()

    @property
    def key(self) -> tuple[int, int]:
        """Grid coordinates as a hashable tuple."""
        return (self._x, self._y)

    @property
    def entity_ids(self) -> set[str]:
        """Read-only view of entity ids occupying this chunk."""
        return self._entity_ids

    def add(self, entity_id: str) -> None:
        """Register an entity in this chunk."""
        self._entity_ids.add(entity_id)

    def remove(self, entity_id: str) -> None:
        """Unregister an entity from this chunk."""
        self._entity_ids.discard(entity_id)

    @property
    def is_empty(self) -> bool:
        """``True`` when no entities occupy this chunk."""
        return len(self._entity_ids) == 0

    def __repr__(self) -> str:
        return f"Chunk({self._x}, {self._y}, entities={len(self._entity_ids)})"