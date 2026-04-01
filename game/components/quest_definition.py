# game/components/quest_definition.py
"""
Immutable blueprint for a quest that can be offered by an NPC.

A ``QuestDefinition`` describes the quest's narrative, objectives,
and rewards.  It is never mutated — the per-character progress is
tracked by ``QuestEntry`` in the character's ``QuestLog``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QuestObjective:
    """
    A single measurable goal within a quest.

    Parameters
    ----------
    objective_id:
        Unique key within the parent quest (e.g. "kill_wolves").
    description:
        Human-readable text (e.g. "Slay 5 Forest Wolves").
    target_id:
        The mob template id or item id the objective tracks.
    required_count:
        How many times the target must be killed / collected.
    """

    objective_id: str
    description: str
    target_id: str
    required_count: int = 1

    def to_dict(self) -> dict:
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "target_id": self.target_id,
            "required_count": self.required_count,
        }


@dataclass(frozen=True)
class QuestReward:
    """
    What the character receives upon turning in the quest.

    Parameters
    ----------
    copper:
        Money reward in copper coins.
    experience:
        XP granted (reserved for future levelling system).
    item_ids:
        List of item ids awarded on completion.
    """

    copper: int = 0
    experience: int = 0
    item_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "copper": self.copper,
            "experience": self.experience,
            "item_ids": list(self.item_ids),
        }


@dataclass(frozen=True)
class QuestDefinition:
    """
    Static template describing a complete quest.

    Parameters
    ----------
    quest_id:
        Globally unique identifier.
    title:
        Short name shown in the quest log.
    description:
        Full narrative text the quest giver delivers.
    giver_entity_id:
        The NPC mob template id that offers this quest.
    level_req:
        Minimum character level required to accept.
    objectives:
        Ordered list of objectives the player must fulfil.
    reward:
        What the player receives upon completion.
    repeatable:
        Whether the quest can be accepted again after turn-in.
    """

    quest_id: str
    title: str
    description: str
    giver_entity_id: str
    level_req: int = 1
    objectives: tuple[QuestObjective, ...] = ()
    reward: QuestReward = field(default_factory=QuestReward)
    repeatable: bool = False

    def to_dict(self) -> dict:
        """Serialise for JSON transport."""
        return {
            "quest_id": self.quest_id,
            "title": self.title,
            "description": self.description,
            "giver_entity_id": self.giver_entity_id,
            "level_req": self.level_req,
            "objectives": [o.to_dict() for o in self.objectives],
            "reward": self.reward.to_dict(),
            "repeatable": self.repeatable,
        }

    def __str__(self) -> str:
        return f"[Quest] {self.title}"