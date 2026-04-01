# game/db/repositories/quest_repo.py
"""Persistence operations for quest definitions and their objectives."""

from __future__ import annotations

import json

from game.db.database import Database


class QuestRepository:
    """
    Read and write quest rows and their linked objectives.

    Parameters
    ----------
    db:
        Active ``Database`` instance.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def save_quest(self, data: dict) -> None:
        """Insert or replace a quest definition row."""
        reward_items = data.get("reward_items", [])
        if isinstance(reward_items, list):
            reward_items = json.dumps(reward_items)

        self._db.execute(
            """
            INSERT OR REPLACE INTO quests
                (id, title, description, giver_entity_id,
                 level_req, reward_copper, reward_xp,
                 reward_items, repeatable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["title"],
                data["description"],
                data["giver_entity_id"],
                data.get("level_req", 1),
                data.get("reward_copper", 0),
                data.get("reward_xp", 0),
                reward_items,
                int(data.get("repeatable", False)),
            ),
        )
        self._db.commit()

    def save_objective(self, data: dict) -> None:
        """Insert a quest objective row."""
        self._db.execute(
            """
            INSERT INTO quest_objectives
                (quest_id, objective_id, description,
                 target_id, required_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["quest_id"],
                data["objective_id"],
                data["description"],
                data["target_id"],
                data.get("required_count", 1),
            ),
        )
        self._db.commit()

    def load_quest(self, quest_id: str) -> dict | None:
        """Load a quest with its objectives, or ``None``."""
        row = self._db.fetchone(
            "SELECT * FROM quests WHERE id = ?", (quest_id,)
        )
        if row is None:
            return None
        d = dict(row)
        d["reward_items"] = json.loads(d["reward_items"])
        d["repeatable"] = bool(d["repeatable"])
        d["objectives"] = self._load_objectives(quest_id)
        return d

    def load_quests_by_giver(self, giver_entity_id: str) -> list[dict]:
        """Return all quests offered by a specific NPC."""
        rows = self._db.fetchall(
            "SELECT * FROM quests WHERE giver_entity_id = ?",
            (giver_entity_id,),
        )
        result = []
        for row in rows:
            d = dict(row)
            d["reward_items"] = json.loads(d["reward_items"])
            d["repeatable"] = bool(d["repeatable"])
            d["objectives"] = self._load_objectives(d["id"])
            result.append(d)
        return result

    def load_all(self) -> list[dict]:
        """Return every quest in the database."""
        rows = self._db.fetchall("SELECT * FROM quests")
        result = []
        for row in rows:
            d = dict(row)
            d["reward_items"] = json.loads(d["reward_items"])
            d["repeatable"] = bool(d["repeatable"])
            d["objectives"] = self._load_objectives(d["id"])
            result.append(d)
        return result

    def _load_objectives(self, quest_id: str) -> list[dict]:
        """Load all objective rows for a quest."""
        rows = self._db.fetchall(
            "SELECT * FROM quest_objectives WHERE quest_id = ? ORDER BY id",
            (quest_id,),
        )
        return [dict(r) for r in rows]