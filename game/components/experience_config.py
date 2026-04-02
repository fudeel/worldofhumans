# game/components/experience_config.py
"""
Centralised experience and levelling configuration.

Every constant and formula governing experience gain, level
thresholds, and kill-reward calculations lives here.  Change
a single parameter to rebalance the entire progression curve.
"""

from __future__ import annotations

import math


# ── tuning knobs ───────────────────────────────────────────────────

MAX_LEVEL: int = 10
"""Hard level cap for all characters."""

BASE_EXP_SEED: int = 30
"""
Experience granted by a level-1 entity.

Higher-level entities use this seed in a diminishing series:
``base_exp(n) = base_exp(n-1) + ceil(BASE_EXP_SEED / n)``.
"""

BASE_LEVEL_COST: int = 250
"""
Multiplied by ``current_level * LEVEL_COST_MULTIPLIER`` to
produce the total XP needed to advance from *current_level*
to the next.
"""

LEVEL_COST_MULTIPLIER: int = 2
"""Scales the cost per level alongside ``BASE_LEVEL_COST``."""

GREY_LEVEL_GAP: int = 5
"""
If the killer's level exceeds the victim's level by more than
this value, the kill awards zero experience.
"""


# ── derived tables (built once at import time) ─────────────────────

def _build_base_exp_table() -> list[int]:
    """
    Pre-compute ``base_exp`` for every level 1 … MAX_LEVEL.

    Level 1  → BASE_EXP_SEED (30)
    Level 2  → prev + ceil(BASE_EXP_SEED / 2)  = 30 + 15 = 45
    Level 3  → prev + ceil(BASE_EXP_SEED / 3)  = 45 + 10 = 55
    Level 4  → prev + ceil(BASE_EXP_SEED / 4)  = 55 +  8 = 63
    …
    """
    table: list[int] = [0]  # index 0 unused
    prev = BASE_EXP_SEED
    table.append(prev)      # level 1
    for lvl in range(2, MAX_LEVEL + 1):
        prev = prev + math.ceil(BASE_EXP_SEED / lvl)
        table.append(prev)
    return table


def _build_level_cost_table() -> list[int]:
    """
    Pre-compute the XP needed to *complete* each level.

    Cost(level) = BASE_LEVEL_COST × level × LEVEL_COST_MULTIPLIER.

    Level 1 → 250 × 1 × 2 =  500
    Level 2 → 250 × 2 × 2 = 1000
    Level 3 → 250 × 3 × 2 = 1500
    …
    """
    table: list[int] = [0]  # index 0 unused
    for lvl in range(1, MAX_LEVEL + 1):
        table.append(BASE_LEVEL_COST * lvl * LEVEL_COST_MULTIPLIER)
    return table


BASE_EXP_BY_LEVEL: list[int] = _build_base_exp_table()
"""
``BASE_EXP_BY_LEVEL[n]`` is the base experience a level-*n*
entity awards when killed.
"""

LEVEL_COST: list[int] = _build_level_cost_table()
"""
``LEVEL_COST[n]`` is the total XP a level-*n* character must
accumulate to advance to level *n + 1*.
"""


# ── public helpers ─────────────────────────────────────────────────

def base_exp_for_level(level: int) -> int:
    """
    Return the base experience a character of *level* awards.

    Clamps to the table boundaries.
    """
    clamped = max(1, min(level, MAX_LEVEL))
    return BASE_EXP_BY_LEVEL[clamped]


def exp_required_for_level(level: int) -> int:
    """
    Return the total XP needed to advance from *level* to *level + 1*.

    Returns ``0`` for characters already at ``MAX_LEVEL``.
    """
    if level >= MAX_LEVEL:
        return 0
    clamped = max(1, min(level, MAX_LEVEL))
    return LEVEL_COST[clamped]


def is_grey_kill(killer_level: int, victim_level: int) -> bool:
    """
    Return ``True`` if the level gap makes the kill worth zero XP.

    A kill is *grey* when ``killer_level - victim_level > GREY_LEVEL_GAP``.
    """
    return (killer_level - victim_level) > GREY_LEVEL_GAP