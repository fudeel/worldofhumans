# game/world/__init__.py
"""World layer: zones, chunks, spatial grid, mob instances, and map objects."""

from game.world.map_object import MapObject
from game.world.map_object_factory import MapObjectFactory
from game.world.map_object_registry import MapObjectRegistry
from game.world.mob_instance import MobInstance
from game.world.spatial_grid import SpatialGrid
from game.world.world import World
from game.world.zone import Zone, ZoneBounds

__all__ = [
    "MapObject",
    "MapObjectFactory",
    "MapObjectRegistry",
    "MobInstance",
    "SpatialGrid",
    "World",
    "Zone",
    "ZoneBounds",
]