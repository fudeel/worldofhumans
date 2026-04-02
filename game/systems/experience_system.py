# game/systems/experience_system.py
"""
Orchestrates experience gain from kills and quest completions.

The ``ExperienceSystem`` is the single entry point for all XP
awards.  It reads the victim's level (for kills) or the quest
reward (for turn-ins), asks the killer's ``ExperienceTracker``
to compute and absorb the XP, and returns a result object the
network layer can forward to the client.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from game.components.experience_tracker import ExperienceTracker, LevelUpResult


@dataclass
class ExperienceGainResult:
    """
    Outcome of an XP-awarding action.

    Attributes
    ----------
    exp_gained:
        Raw XP added to the character.
    tracker_snapshot:
        Serialised state of the tracker after the award.
    level_up:
        Present only when the character levelled up.
    """

    exp_gained: int
    tracker_snapshot: dict
    level_up: LevelUpResult | None = None


class ExperienceSystem:
    """
    Stateless facade for awarding experience points.

    All XP sources (mob kills, player kills, quest rewards)
    funnel through this system so the rules are applied
    uniformly.
    """

    # -- kill XP -------------------------------------------------------------

    @staticmethod
    def award_kill_exp(
        killer_tracker: ExperienceTracker,
        victim_level: int,
    ) -> Optional[ExperienceGainResult]:
        """
        Grant kill experience to *killer_tracker*.

        Returns ``None`` when the kill is grey (victim too low)
        or the killer is at max level.

        Parameters
        ----------
        killer_tracker:
            The ``ExperienceTracker`` of the character that scored
            the kill.
        victim_level:
            Level of the slain entity.
        """
        amount = killer_tracker.compute_kill_exp(victim_level)
        if amount <= 0:
            return None

        level_up = killer_tracker.add_experience(amount)
        return ExperienceGainResult(
            exp_gained=amount,
            tracker_snapshot=killer_tracker.to_dict(),
            level_up=level_up,
        )

    # -- quest XP ------------------------------------------------------------

    @staticmethod
    def award_quest_exp(
        tracker: ExperienceTracker,
        quest_exp: int,
    ) -> Optional[ExperienceGainResult]:
        """
        Grant quest-completion experience to *tracker*.

        Quests always award their full XP regardless of level
        difference.  Returns ``None`` only when ``quest_exp``
        is zero or the character is max level.

        Parameters
        ----------
        tracker:
            The ``ExperienceTracker`` of the completing character.
        quest_exp:
            XP amount specified in the quest reward.
        """
        if quest_exp <= 0:
            return None

        level_up = tracker.add_experience(quest_exp)
        return ExperienceGainResult(
            exp_gained=quest_exp,
            tracker_snapshot=tracker.to_dict(),
            level_up=level_up,
        )