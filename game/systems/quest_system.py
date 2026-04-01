# game/systems/quest_system.py
"""
Central quest registry and interaction handler.

The ``QuestSystem`` loads quest definitions from the database
at boot and provides methods for offering, accepting, progressing,
and completing quests.  It works together with each character's
``QuestLog`` component.
"""

from __future__ import annotations

from typing import Optional

from game.characters.character import Character
from game.components.item import Item
from game.components.quest_definition import (
    QuestDefinition,
    QuestObjective,
    QuestReward,
)
from game.components.quest_log import QuestEntry


class QuestSystem:
    """
    Global quest catalogue and interaction facade.

    Parameters
    ----------
    quest_definitions:
        Mapping of quest_id → ``QuestDefinition``.
    giver_quests:
        Mapping of giver_entity_id → list of quest_ids.
    item_catalogue:
        Mapping of item_id → ``Item`` (for reward lookups).
    """

    def __init__(
        self,
        quest_definitions: dict[str, QuestDefinition],
        giver_quests: dict[str, list[str]],
        item_catalogue: dict[str, Item],
    ) -> None:
        self._quests = quest_definitions
        self._giver_quests = giver_quests
        self._items = item_catalogue

    # -- read-only -----------------------------------------------------------

    def get_definition(self, quest_id: str) -> Optional[QuestDefinition]:
        """Look up a quest blueprint by id."""
        return self._quests.get(quest_id)

    def get_quests_for_giver(self, giver_entity_id: str) -> list[QuestDefinition]:
        """Return all quests offered by the given NPC."""
        ids = self._giver_quests.get(giver_entity_id, [])
        return [self._quests[qid] for qid in ids if qid in self._quests]

    def get_available_quests_for(
        self,
        giver_entity_id: str,
        character: Character,
    ) -> list[QuestDefinition]:
        """
        Return quests the NPC can offer that the character can accept.

        Filters out quests already in progress, below level req,
        or already turned in (unless repeatable).
        """
        available: list[QuestDefinition] = []
        for qdef in self.get_quests_for_giver(giver_entity_id):
            if character.level < qdef.level_req:
                continue
            entry = character.quest_log.get_entry(qdef.quest_id)
            if entry is None:
                available.append(qdef)
            elif entry.status.value == "turned_in" and qdef.repeatable:
                available.append(qdef)
        return available

    # -- mutations -----------------------------------------------------------

    def accept_quest(
        self,
        character: Character,
        quest_id: str,
    ) -> Optional[QuestEntry]:
        """
        Have *character* accept the quest identified by *quest_id*.

        Returns the new ``QuestEntry`` on success, or ``None`` on failure
        (quest not found, log full, already tracking, level too low).
        """
        qdef = self._quests.get(quest_id)
        if qdef is None:
            return None
        if character.level < qdef.level_req:
            return None
        return character.quest_log.accept_quest(qdef)

    def on_mob_killed(
        self,
        character: Character,
        mob_template_id: str,
    ) -> list[QuestEntry]:
        """
        Notify the character's quest log that a mob was killed.

        Returns a list of quest entries that became ``COMPLETED``.
        """
        return character.quest_log.advance_objective(mob_template_id)

    def turn_in_quest(
        self,
        character: Character,
        quest_id: str,
    ) -> Optional[QuestEntry]:
        """
        Turn in a completed quest and grant rewards.

        Returns the turned-in entry, or ``None`` if the quest is
        not completed or not in the log.
        """
        entry = character.quest_log.turn_in(quest_id)
        if entry is None:
            return None

        reward = entry.definition.reward
        if reward.copper > 0:
            character.currency.add(reward.copper)
        for item_id in reward.item_ids:
            item = self._items.get(item_id)
            if item is not None:
                character.inventory.add_item(item)

        return entry

    def abandon_quest(
        self,
        character: Character,
        quest_id: str,
    ) -> Optional[QuestEntry]:
        """Remove a quest from the character's log."""
        return character.quest_log.abandon_quest(quest_id)

    # -- factory helper ------------------------------------------------------

    @staticmethod
    def build_from_db_rows(
        quest_rows: list[dict],
        item_catalogue: dict[str, Item],
    ) -> "QuestSystem":
        """
        Construct a ``QuestSystem`` from database query results.

        Parameters
        ----------
        quest_rows:
            Output of ``QuestRepository.load_all()``.
        item_catalogue:
            The global item id → ``Item`` mapping.
        """
        definitions: dict[str, QuestDefinition] = {}
        giver_map: dict[str, list[str]] = {}

        for row in quest_rows:
            objectives = tuple(
                QuestObjective(
                    objective_id=o["objective_id"],
                    description=o["description"],
                    target_id=o["target_id"],
                    required_count=o.get("required_count", 1),
                )
                for o in row.get("objectives", [])
            )
            reward = QuestReward(
                copper=row.get("reward_copper", 0),
                experience=row.get("reward_xp", 0),
                item_ids=row.get("reward_items", []),
            )
            qdef = QuestDefinition(
                quest_id=row["id"],
                title=row["title"],
                description=row["description"],
                giver_entity_id=row["giver_entity_id"],
                level_req=row.get("level_req", 1),
                objectives=objectives,
                reward=reward,
                repeatable=bool(row.get("repeatable", False)),
            )
            definitions[qdef.quest_id] = qdef
            giver_map.setdefault(qdef.giver_entity_id, []).append(qdef.quest_id)

        return QuestSystem(definitions, giver_map, item_catalogue)