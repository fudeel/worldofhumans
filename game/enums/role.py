# game/enums/role.py
"""Combat roles a character can fulfil."""

from enum import Enum


class Role(Enum):
    """Defines the function a character serves in group content."""

    TANK = "Tank"
    HEALER = "Healer"
    MELEE_DPS = "Melee DPS"
    RANGED_DPS = "Ranged DPS"