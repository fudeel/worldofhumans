# game/enums/resource_type.py
"""Types of resources consumed by characters during combat."""

from enum import Enum


class ResourceType(Enum):
    """
    Primary resource types used by character abilities.

    Every living entity has HEALTH.  Secondary resources vary by class
    and, in the case of Druids, by active shapeshift form.
    """

    HEALTH = "Health"
    MANA = "Mana"
    RAGE = "Rage"
    ENERGY = "Energy"