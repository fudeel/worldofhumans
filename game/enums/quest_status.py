# game/enums/quest_status.py
"""Progression states for a quest bound to a character."""

from enum import Enum


class QuestStatus(Enum):
    """
    Lifecycle states a quest passes through once accepted.

    ``AVAILABLE``  → shown on the quest giver, not yet accepted.
    ``IN_PROGRESS`` → accepted and actively being worked on.
    ``COMPLETED``   → objectives met, ready to turn in.
    ``TURNED_IN``   → rewards claimed; quest is finished.
    ``FAILED``      → time-sensitive quest expired or was abandoned.
    """

    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TURNED_IN = "turned_in"
    FAILED = "failed"