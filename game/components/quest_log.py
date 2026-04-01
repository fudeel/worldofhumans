# game/components/quest_log.py
"""
Per-character quest journal tracking accepted quests and progress.

The ``QuestLog`` stores ``QuestEntry`` instances that pair a
``QuestDefinition`` with mutable objective counters and a status.
It enforces a maximum number of simultaneous active quests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from game.components.quest_definition import QuestDefinition, QuestObjective
from game.enums.quest_status import QuestStatus


MAX_ACTIVE_QUESTS = 10
"""Hard cap on how many quests a character can hold simultaneously."""


@dataclass
class ObjectiveProgress:
    """
    Mutable counter for a single quest objective.

    Attributes
    ----------
    objective:
        The immutable objective blueprint.
    current_count:
        How many kills / items the player has achieved so far.
    """

    objective: QuestObjective
    current_count: int = 0

    @property
    def is_complete(self) -> bool:
        """``True`` when the required count is met."""
        return self.current_count >= self.objective.required_count

    def increment(self, amount: int = 1) -> None:
        """Advance the counter, clamping at the required count."""
        self.current_count = min(
            self.current_count + amount,
            self.objective.required_count,
        )

    def to_dict(self) -> dict:
        return {
            "objective_id": self.objective.objective_id,
            "description": self.objective.description,
            "target_id": self.objective.target_id,
            "current_count": self.current_count,
            "required_count": self.objective.required_count,
            "is_complete": self.is_complete,
        }


@dataclass
class QuestEntry:
    """
    A single quest accepted by the character.

    Attributes
    ----------
    definition:
        The quest's static blueprint.
    status:
        Current lifecycle state.
    progress:
        Per-objective counters.
    """

    definition: QuestDefinition
    status: QuestStatus = QuestStatus.IN_PROGRESS
    progress: list[ObjectiveProgress] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.progress:
            self.progress = [
                ObjectiveProgress(objective=obj)
                for obj in self.definition.objectives
            ]

    @property
    def all_objectives_complete(self) -> bool:
        """``True`` when every objective counter is satisfied."""
        return all(p.is_complete for p in self.progress)

    def to_dict(self) -> dict:
        return {
            "quest_id": self.definition.quest_id,
            "title": self.definition.title,
            "description": self.definition.description,
            "status": self.status.value,
            "objectives": [p.to_dict() for p in self.progress],
            "reward": self.definition.reward.to_dict(),
        }


class QuestLog:
    """
    Container for all quests a character has accepted.

    Parameters
    ----------
    max_quests:
        Maximum simultaneous active quests.
    """

    def __init__(self, max_quests: int = MAX_ACTIVE_QUESTS) -> None:
        self._max = max_quests
        self._entries: dict[str, QuestEntry] = {}

    # -- read-only -----------------------------------------------------------

    @property
    def active_count(self) -> int:
        """Number of quests currently in progress."""
        return sum(
            1 for e in self._entries.values()
            if e.status == QuestStatus.IN_PROGRESS
        )

    @property
    def is_full(self) -> bool:
        """``True`` if no more quests can be accepted."""
        return self.active_count >= self._max

    def get_entry(self, quest_id: str) -> Optional[QuestEntry]:
        """Return the entry for *quest_id*, or ``None``."""
        return self._entries.get(quest_id)

    def has_quest(self, quest_id: str) -> bool:
        """``True`` if *quest_id* is in the log (any status)."""
        return quest_id in self._entries

    def get_all_entries(self) -> list[QuestEntry]:
        """Return all quest entries."""
        return list(self._entries.values())

    def get_active_entries(self) -> list[QuestEntry]:
        """Return only in-progress quests."""
        return [
            e for e in self._entries.values()
            if e.status == QuestStatus.IN_PROGRESS
        ]

    # -- mutations -----------------------------------------------------------

    def accept_quest(self, definition: QuestDefinition) -> Optional[QuestEntry]:
        """
        Add a quest to the log.

        Returns the new ``QuestEntry`` on success, or ``None`` if
        the log is full or the quest is already tracked.
        """
        if self.is_full:
            return None
        if definition.quest_id in self._entries:
            existing = self._entries[definition.quest_id]
            if existing.status != QuestStatus.TURNED_IN or not definition.repeatable:
                return None

        entry = QuestEntry(definition=definition)
        self._entries[definition.quest_id] = entry
        return entry

    def advance_objective(self, target_id: str, amount: int = 1) -> list[QuestEntry]:
        """
        Increment counters on every active quest that tracks *target_id*.

        Returns a list of quest entries whose status changed to
        ``COMPLETED`` as a result of this call.
        """
        newly_completed: list[QuestEntry] = []
        for entry in self._entries.values():
            if entry.status != QuestStatus.IN_PROGRESS:
                continue
            for prog in entry.progress:
                if prog.objective.target_id == target_id and not prog.is_complete:
                    prog.increment(amount)
            if entry.all_objectives_complete:
                entry.status = QuestStatus.COMPLETED
                newly_completed.append(entry)
        return newly_completed

    def turn_in(self, quest_id: str) -> Optional[QuestEntry]:
        """
        Mark a completed quest as turned in.

        Returns the entry if successful, ``None`` otherwise.
        """
        entry = self._entries.get(quest_id)
        if entry is None or entry.status != QuestStatus.COMPLETED:
            return None
        entry.status = QuestStatus.TURNED_IN
        return entry

    def abandon_quest(self, quest_id: str) -> Optional[QuestEntry]:
        """
        Remove a quest from the log.

        Returns the removed entry, or ``None`` if not found.
        """
        entry = self._entries.pop(quest_id, None)
        if entry is not None:
            entry.status = QuestStatus.FAILED
        return entry

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the entire log for JSON transport."""
        return {
            "max_quests": self._max,
            "entries": [e.to_dict() for e in self._entries.values()],
        }

    def __repr__(self) -> str:
        return f"QuestLog({self.active_count}/{self._max})"