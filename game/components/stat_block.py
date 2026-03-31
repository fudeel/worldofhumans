# game/components/stat_block.py
"""Collection of character statistics with base and bonus tracking."""

from __future__ import annotations

from game.enums.stat_type import StatType


class StatBlock:
    """
    Holds every stat a character can have.

    Stats are split into a *base* value (from race, class, and level) and
    a *bonus* value (from gear, buffs, and talents).  The effective total
    is always ``base + bonus``.

    Parameters
    ----------
    base_stats:
        Initial base values keyed by ``StatType``.  Missing stats
        default to ``0``.
    """

    def __init__(self, base_stats: dict[StatType, int] | None = None) -> None:
        self._base: dict[StatType, int] = dict(base_stats) if base_stats else {}
        self._bonus: dict[StatType, int] = {}

    # -- read ----------------------------------------------------------------

    def get_base(self, stat: StatType) -> int:
        """Return the raw base value for *stat*."""
        return self._base.get(stat, 0)

    def get_bonus(self, stat: StatType) -> int:
        """Return the accumulated bonus for *stat*."""
        return self._bonus.get(stat, 0)

    def get_total(self, stat: StatType) -> int:
        """Return ``base + bonus`` for *stat*."""
        return self.get_base(stat) + self.get_bonus(stat)

    # -- write ---------------------------------------------------------------

    def set_base(self, stat: StatType, value: int) -> None:
        """Overwrite the base value for *stat*."""
        self._base[stat] = value

    def add_bonus(self, stat: StatType, amount: int) -> None:
        """Increase the bonus for *stat* by *amount* (may be negative)."""
        self._bonus[stat] = self._bonus.get(stat, 0) + amount

    def remove_bonus(self, stat: StatType, amount: int) -> None:
        """Decrease the bonus for *stat* by *amount*."""
        self.add_bonus(stat, -amount)

    def clear_bonuses(self) -> None:
        """Remove all bonus modifiers (e.g. on buff expiry)."""
        self._bonus.clear()

    # -- bulk ----------------------------------------------------------------

    def apply_base_stats(self, stats: dict[StatType, int]) -> None:
        """Merge a dictionary of base values, overwriting existing ones."""
        self._base.update(stats)

    # -- dunder --------------------------------------------------------------

    def __repr__(self) -> str:
        non_zero = {
            s.value: self.get_total(s)
            for s in StatType
            if self.get_total(s) != 0
        }
        return f"StatBlock({non_zero})"