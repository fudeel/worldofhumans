# game/components/resource_pool.py
"""A single depletable resource such as Health, Mana, Rage, or Energy."""

from __future__ import annotations

from game.enums.resource_type import ResourceType


class ResourcePool:
    """
    Tracks one resource with a current and maximum value.

    The current value is clamped between ``0`` and ``maximum`` on every
    mutation so callers never need to bounds-check themselves.

    Parameters
    ----------
    resource_type:
        Which resource this pool represents.
    maximum:
        Upper bound for the pool.  Also used as the starting value.
    """

    def __init__(self, resource_type: ResourceType, maximum: int) -> None:
        self._type = resource_type
        self._maximum = max(0, maximum)
        self._current = self._maximum

    # -- public properties ---------------------------------------------------

    @property
    def resource_type(self) -> ResourceType:
        """The kind of resource stored in this pool."""
        return self._type

    @property
    def current(self) -> int:
        """Current amount available."""
        return self._current

    @property
    def maximum(self) -> int:
        """Upper limit of the pool."""
        return self._maximum

    @property
    def is_empty(self) -> bool:
        """``True`` when the current value has reached zero."""
        return self._current <= 0

    @property
    def is_full(self) -> bool:
        """``True`` when current equals maximum."""
        return self._current >= self._maximum

    @property
    def percentage(self) -> float:
        """Current value as a percentage of maximum (0.0 – 100.0)."""
        if self._maximum == 0:
            return 0.0
        return (self._current / self._maximum) * 100.0

    # -- mutators ------------------------------------------------------------

    def consume(self, amount: int) -> int:
        """
        Subtract *amount* from the pool and return the amount actually consumed.

        If the pool has less than *amount*, only the remaining value is
        consumed and the pool drops to zero.
        """
        actual = min(amount, self._current)
        self._current = max(0, self._current - actual)
        return actual

    def restore(self, amount: int) -> int:
        """
        Add *amount* to the pool and return the amount actually restored.

        The pool will not exceed its maximum.
        """
        headroom = self._maximum - self._current
        actual = min(amount, headroom)
        self._current += actual
        return actual

    def set_maximum(self, new_max: int) -> None:
        """
        Update the pool's maximum and clamp current accordingly.

        Useful when gear or buffs modify the cap at runtime.
        """
        self._maximum = max(0, new_max)
        self._current = min(self._current, self._maximum)

    def reset(self) -> None:
        """Refill the pool to its maximum value."""
        self._current = self._maximum

    # -- dunder --------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ResourcePool({self._type.value}: "
            f"{self._current}/{self._maximum})"
        )