# game/world/world.py
"""
Top-level world manager.

Owns every gaming zone, every live entity, and enforces the
zone-gate rule: entities outside all zones are tracked by
position only — they receive no world data and are invisible
to other players.
"""

from __future__ import annotations

from game.characters.living_entity import LivingEntity
from game.world.spatial_grid import SpatialGrid
from game.world.zone import Zone


class World:
    """
    The entire game world.

    Tracks which zone (if any) each entity belongs to, and
    delegates spatial queries to the appropriate zone grid.
    """

    def __init__(self) -> None:
        self._zones: dict[str, Zone] = {}
        self._zone_grids: dict[str, SpatialGrid] = {}
        self._entities: dict[str, LivingEntity] = {}
        self._entity_positions: dict[str, tuple[float, float]] = {}
        self._entity_zone: dict[str, str] = {}

    # -- zone management -----------------------------------------------------

    def add_zone(self, zone: Zone) -> None:
        """Register a gaming zone in the world."""
        self._zones[zone.zone_id] = zone
        self._zone_grids[zone.zone_id] = SpatialGrid(zone.chunk_size)

    def get_zone(self, zone_id: str) -> Zone | None:
        """Retrieve a zone by id."""
        return self._zones.get(zone_id)

    def get_all_zones(self) -> list[Zone]:
        """Return every registered zone."""
        return list(self._zones.values())

    def find_zone_at(self, x: float, y: float) -> Zone | None:
        """Return the zone containing the point (x, y), or ``None``."""
        for zone in self._zones.values():
            if zone.contains(x, y):
                return zone
        return None

    # -- entity management ---------------------------------------------------

    def add_entity(self, entity: LivingEntity, x: float, y: float) -> str | None:
        """
        Place an entity in the world at (x, y).

        If the position falls inside a gaming zone the entity is
        added to that zone's spatial grid.  Returns the zone id
        the entity landed in, or ``None`` if outside all zones.
        """
        eid = entity.name
        self._entities[eid] = entity
        self._entity_positions[eid] = (x, y)

        zone = self.find_zone_at(x, y)
        if zone:
            self._entity_zone[eid] = zone.zone_id
            self._zone_grids[zone.zone_id].add_entity(eid, x, y)
            return zone.zone_id
        return None

    def remove_entity(self, entity_id: str) -> None:
        """Remove an entity from the world entirely."""
        zone_id = self._entity_zone.pop(entity_id, None)
        if zone_id and zone_id in self._zone_grids:
            self._zone_grids[zone_id].remove_entity(entity_id)
        self._entities.pop(entity_id, None)
        self._entity_positions.pop(entity_id, None)

    def get_entity(self, entity_id: str) -> LivingEntity | None:
        """Retrieve a live entity by id."""
        return self._entities.get(entity_id)

    def get_entity_position(self, entity_id: str) -> tuple[float, float] | None:
        """Return an entity's current (x, y), or ``None``."""
        return self._entity_positions.get(entity_id)

    def get_entity_zone_id(self, entity_id: str) -> str | None:
        """Return the zone id an entity is in, or ``None`` if outside."""
        return self._entity_zone.get(entity_id)

    def is_entity_in_zone(self, entity_id: str) -> bool:
        """``True`` if the entity is inside a gaming zone."""
        return entity_id in self._entity_zone

    # -- movement with zone transitions --------------------------------------

    def move_entity(self, entity_id: str, new_x: float, new_y: float) -> dict:
        """
        Update an entity's position and handle zone transitions.

        Returns a dict describing what happened::

            {"entered_zone": Zone | None,
             "left_zone": str | None,
             "current_zone_id": str | None}
        """
        result: dict = {"entered_zone": None, "left_zone": None, "current_zone_id": None}
        old_zone_id = self._entity_zone.get(entity_id)
        new_zone = self.find_zone_at(new_x, new_y)
        new_zone_id = new_zone.zone_id if new_zone else None

        self._entity_positions[entity_id] = (new_x, new_y)

        if old_zone_id == new_zone_id:
            if new_zone_id:
                self._zone_grids[new_zone_id].move_entity(entity_id, new_x, new_y)
            result["current_zone_id"] = new_zone_id
            return result

        if old_zone_id:
            self._zone_grids[old_zone_id].remove_entity(entity_id)
            del self._entity_zone[entity_id]
            result["left_zone"] = old_zone_id

        if new_zone_id:
            self._zone_grids[new_zone_id].add_entity(entity_id, new_x, new_y)
            self._entity_zone[entity_id] = new_zone_id
            result["entered_zone"] = new_zone
            result["current_zone_id"] = new_zone_id

        return result

    # -- spatial queries (zone-gated) ----------------------------------------

    def get_nearby_entity_ids(self, entity_id: str) -> set[str]:
        """
        Return entity ids near *entity_id*.

        Returns an empty set if the entity is outside all zones
        — this is the zone-gate in action.
        """
        zone_id = self._entity_zone.get(entity_id)
        if not zone_id:
            return set()
        pos = self._entity_positions.get(entity_id)
        if not pos:
            return set()
        return self._zone_grids[zone_id].get_nearby_entity_ids(pos[0], pos[1])

    def get_entities_in_zone(self, zone_id: str) -> list[str]:
        """Return all entity ids currently inside the given zone."""
        return [
            eid for eid, zid in self._entity_zone.items()
            if zid == zone_id
        ]