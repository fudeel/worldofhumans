# game/enums/mob_state.py
"""Finite-state-machine states for mob AI behaviour."""

from enum import Enum


class MobState(Enum):
    """
    Each mob is in exactly one state at any time.

    Transitions are driven by the ``MobBrain`` every tick.

    IDLE            → standing at or near spawn, doing nothing.
    PATROL          → wandering randomly within patrol radius.
    CHASE           → moving toward a targeted player.
    ATTACK          → within strike range, dealing damage.
    RETURN_TO_SPAWN → pulled too far from spawn, walking back.
    DEAD            → waiting for respawn timer.
    """

    IDLE = "idle"
    PATROL = "patrol"
    CHASE = "chase"
    ATTACK = "attack"
    RETURN_TO_SPAWN = "return_to_spawn"
    DEAD = "dead"