# game/components/experience_tracker.py
"""
Per-character experience and level-up tracking.

An ``ExperienceTracker`` is attached to every ``LivingEntity``
that can earn experience (both player characters and mobs).
It holds the current XP, delegates all threshold and reward
maths to ``experience_config``, and emits level-up information
when the threshold is crossed.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.components.experience_config import (
    MAX_LEVEL,
    base_exp_for_level,
    exp_required_for_level,
    is_grey_kill,
)


@dataclass
class LevelUpResult:
    """
    Returned by ``ExperienceTracker.add_experience`` when one or
    more level-ups occur.

    Attributes
    ----------
    old_level:
        Level before the XP was added.
    new_level:
        Level after all level-ups resolved.
    levels_gained:
        Number of levels gained in this single call.
    """

    old_level: int
    new_level: int
    levels_gained: int


class ExperienceTracker:
    """
    Tracks current XP and handles level advancement.

    Parameters
    ----------
    level:
        Starting level of the owning entity.
    current_exp:
        Pre-existing experience within the current level.
    """

    def __init__(self, level: int = 1, current_exp: int = 0) -> None:
        self._level = max(1, min(level, MAX_LEVEL))
        self._current_exp = current_exp

    # -- read-only -----------------------------------------------------------

    @property
    def level(self) -> int:
        """Current character level."""
        return self._level

    @property
    def current_exp(self) -> int:
        """XP accumulated within the current level."""
        return self._current_exp

    @property
    def exp_to_next_level(self) -> int:
        """Total XP required to reach the next level."""
        return exp_required_for_level(self._level)

    @property
    def is_max_level(self) -> bool:
        """``True`` when the character has reached the level cap."""
        return self._level >= MAX_LEVEL

    @property
    def base_exp_reward(self) -> int:
        """XP this entity awards to its killer."""
        return base_exp_for_level(self._level)

    # -- mutations -----------------------------------------------------------

    def add_experience(self, amount: int) -> LevelUpResult | None:
        """
        Grant *amount* XP and process any resulting level-ups.

        Returns a ``LevelUpResult`` if at least one level was gained,
        or ``None`` if no level-up occurred.
        """
        if amount <= 0 or self.is_max_level:
            return None

        old_level = self._level
        self._current_exp += amount

        while not self.is_max_level:
            required = exp_required_for_level(self._level)
            if required == 0 or self._current_exp < required:
                break
            self._current_exp -= required
            self._level += 1

        if self._level > old_level:
            return LevelUpResult(
                old_level=old_level,
                new_level=self._level,
                levels_gained=self._level - old_level,
            )
        return None

    def compute_kill_exp(self, victim_level: int) -> int:
        """
        Calculate the XP earned for killing a victim of *victim_level*.

        Returns ``0`` if the kill is grey (victim too low).
        """
        if is_grey_kill(self._level, victim_level):
            return 0
        return base_exp_for_level(victim_level)

    def reset(self, level: int = 1, current_exp: int = 0) -> None:
        """
        Reset experience state (used on mob respawn).

        Mobs respawn at their template level with zero XP.
        """
        self._level = max(1, min(level, MAX_LEVEL))
        self._current_exp = current_exp

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise for JSON transport to the frontend."""
        return {
            "level": self._level,
            "current_exp": self._current_exp,
            "exp_to_next_level": self.exp_to_next_level,
            "is_max_level": self.is_max_level,
        }

    def __repr__(self) -> str:
        return (
            f"ExperienceTracker(lv{self._level}, "
            f"{self._current_exp}/{self.exp_to_next_level} XP)"
        )