# game/db/repositories/mob_template_repo.py
"""Persistence operations for mob spawn templates."""

from __future__ import annotations

import json

from game.db.database import Database


class MobTemplateRepository:
    """
    Read and write mob template rows in the ``mob_templates`` table.

    Parameters
    ----------
    db:
        Active ``Database`` instance.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, data: dict) -> None:
        """Insert or replace a mob template row."""
        stats = data.get("stats_json", {})
        if isinstance(stats, dict):
            stats = json.dumps(stats)

        self._db.execute(
            """
            INSERT OR REPLACE INTO mob_templates
                (id, name, class, level, base_health, base_mana,
                 spawn_x, spawn_y, zone_id, respawn_sec,
                 aggression_type, aggro_range, attack_range,
                 leash_range, patrol_radius, move_speed,
                 attack_cooldown, drop_money_min, drop_money_max,
                 is_quest_giver, is_vendor, stats_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"], data["name"], data["class"],
                data["level"], data["base_health"], data["base_mana"],
                data["spawn_x"], data["spawn_y"],
                data["zone_id"], data["respawn_sec"],
                data.get("aggression_type", "passive"),
                data.get("aggro_range", 80.0),
                data.get("attack_range", 5.0),
                data.get("leash_range", 200.0),
                data.get("patrol_radius", 30.0),
                data.get("move_speed", 40.0),
                data.get("attack_cooldown", 2.0),
                data.get("drop_money_min", 0),
                data.get("drop_money_max", 0),
                int(data.get("is_quest_giver", False)),
                int(data.get("is_vendor", False)),
                stats,
            ),
        )
        self._db.commit()

    def load_by_zone(self, zone_id: str) -> list[dict]:
        """Return all mob templates assigned to *zone_id*."""
        rows = self._db.fetchall(
            "SELECT * FROM mob_templates WHERE zone_id = ?", (zone_id,)
        )
        result = []
        for row in rows:
            d = dict(row)
            d["stats_json"] = json.loads(d["stats_json"])
            d["is_quest_giver"] = bool(d["is_quest_giver"])
            d["is_vendor"] = bool(d["is_vendor"])
            result.append(d)
        return result

    def load(self, mob_id: str) -> dict | None:
        """Load a single mob template row by id."""
        row = self._db.fetchone(
            "SELECT * FROM mob_templates WHERE id = ?", (mob_id,)
        )
        if row is None:
            return None
        d = dict(row)
        d["stats_json"] = json.loads(d["stats_json"])
        d["is_quest_giver"] = bool(d["is_quest_giver"])
        d["is_vendor"] = bool(d["is_vendor"])
        return d