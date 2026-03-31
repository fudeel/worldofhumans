# game/world/spatial_grid.py
"""
Spatial grid for a single gaming zone.

Divides the zone into fixed-size chunks and provides O(1)
lookups for "which entities are near this position?" by
returning the contents of the target chunk plus its eight
neighbours.
"""

from __future__ import annotations

from game.world.chunk import Chunk


class SpatialGrid:
    """
    Grid of chunks covering one zone's area.

    Chunks are created lazily on first access so empty regions
    consume no memory.

    Parameters
    ----------
    chunk_size:
        Side length of each square chunk in world units.
    """

    def __init__(self, chunk_size: int = 100) -> None:
        self._chunk_size = chunk_size
        self._chunks: dict[tuple[int, int], Chunk] = {}
        self._entity_chunk: dict[str, tuple[int, int]] = {}

    # -- coordinate helpers --------------------------------------------------

    def _to_chunk_key(self, x: float, y: float) -> tuple[int, int]:
        """Convert a world position to its chunk grid coordinates."""
        return (int(x // self._chunk_size), int(y // self._chunk_size))

    def _get_or_create(self, key: tuple[int, int]) -> Chunk:
        """Return the chunk at *key*, creating it if necessary."""
        if key not in self._chunks:
            self._chunks[key] = Chunk(key[0], key[1])
        return self._chunks[key]

    # -- entity management ---------------------------------------------------

    def add_entity(self, entity_id: str, x: float, y: float) -> None:
        """Place an entity into the chunk covering (x, y)."""
        key = self._to_chunk_key(x, y)
        self._get_or_create(key).add(entity_id)
        self._entity_chunk[entity_id] = key

    def remove_entity(self, entity_id: str) -> None:
        """Remove an entity from whatever chunk it occupies."""
        key = self._entity_chunk.pop(entity_id, None)
        if key and key in self._chunks:
            self._chunks[key].remove(entity_id)
            if self._chunks[key].is_empty:
                del self._chunks[key]

    def move_entity(self, entity_id: str, new_x: float, new_y: float) -> None:
        """
        Update an entity's chunk after it moves.

        Only performs a chunk transfer if the new position falls
        in a different chunk than the current one.
        """
        new_key = self._to_chunk_key(new_x, new_y)
        old_key = self._entity_chunk.get(entity_id)

        if old_key == new_key:
            return

        if old_key and old_key in self._chunks:
            self._chunks[old_key].remove(entity_id)
            if self._chunks[old_key].is_empty:
                del self._chunks[old_key]

        self._get_or_create(new_key).add(entity_id)
        self._entity_chunk[entity_id] = new_key

    # -- queries -------------------------------------------------------------

    def get_nearby_entity_ids(self, x: float, y: float) -> set[str]:
        """
        Return all entity ids in the chunk at (x, y) and its
        eight neighbouring chunks (the 3×3 interest area).
        """
        cx, cy = self._to_chunk_key(x, y)
        result: set[str] = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                chunk = self._chunks.get((cx + dx, cy + dy))
                if chunk:
                    result.update(chunk.entity_ids)
        return result

    def get_entity_chunk_key(self, entity_id: str) -> tuple[int, int] | None:
        """Return the chunk key an entity occupies, or ``None``."""
        return self._entity_chunk.get(entity_id)