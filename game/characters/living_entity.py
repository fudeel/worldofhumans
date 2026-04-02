# game/characters/living_entity.py
"""
Base class for every living thing in the game world.

Both player-controlled and server-controlled characters inherit from
``LivingEntity``.  It provides the minimum shared contract: a name,
a health pool, an experience tracker, and the ability to take damage
and die.
"""

from __future__ import annotations

from game.components.experience_tracker import ExperienceTracker
from game.components.resource_pool import ResourcePool
from game.enums.resource_type import ResourceType


class LivingEntity:
    """
    Anything in the game world that is alive and can die.

    Parameters
    ----------
    name:
        Display name of the entity.
    max_health:
        Starting (and maximum) hit-point value.
    level:
        Current level of the entity.
    """

    def __init__(self, name: str, max_health: int, level: int = 1) -> None:
        self._name = name
        self._level = level
        self._health = ResourcePool(ResourceType.HEALTH, max_health)
        self._alive = True
        self._experience = ExperienceTracker(level=level)

    # -- identity ------------------------------------------------------------

    @property
    def name(self) -> str:
        """Display name."""
        return self._name

    @property
    def level(self) -> int:
        """Current level (delegates to experience tracker)."""
        return self._experience.level

    @level.setter
    def level(self, value: int) -> None:
        self._level = max(1, value)

    # -- health --------------------------------------------------------------

    @property
    def health(self) -> ResourcePool:
        """The entity's health pool."""
        return self._health

    @property
    def is_alive(self) -> bool:
        """``True`` while the entity has health remaining."""
        return self._alive

    # -- experience ----------------------------------------------------------

    @property
    def experience(self) -> ExperienceTracker:
        """The entity's experience and levelling tracker."""
        return self._experience

    # -- combat interface ----------------------------------------------------

    def take_damage(self, amount: int) -> int:
        """
        Inflict *amount* damage and return the actual damage dealt.

        If health reaches zero the entity is marked dead.
        """
        actual = self._health.consume(amount)
        if self._health.is_empty:
            self._alive = False
        return actual

    def receive_healing(self, amount: int) -> int:
        """
        Heal *amount* health and return the actual amount restored.

        Has no effect on a dead entity.
        """
        if not self._alive:
            return 0
        return self._health.restore(amount)

    def resurrect(self, health_pct: float = 100.0) -> None:
        """
        Bring a dead entity back to life at *health_pct* % of max health.

        Does nothing if the entity is already alive.
        """
        if self._alive:
            return
        restore = max(1, int(self._health.maximum * health_pct / 100.0))
        self._health.restore(restore)
        self._alive = True

    # -- dunder --------------------------------------------------------------

    def __repr__(self) -> str:
        status = "alive" if self._alive else "dead"
        return f"LivingEntity('{self._name}', lv{self.level}, {status})"