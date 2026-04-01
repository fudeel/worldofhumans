# game/systems/loot_system.py
"""
Manages loot generation and pickup for dead mobs.

When a mob dies the ``LootSystem`` rolls its loot table and
creates a ``LootDrop`` at the death position.  When the mob
respawns the drop is automatically invalidated.

The system is intentionally stateless between ticks — all
active drops live in an in-memory dict keyed by drop_id.
"""

from __future__ import annotations

import random
from typing import Optional

from game.components.item import Item
from game.components.loot_drop import LootDrop
from game.enums.item_slot import ItemSlot
from game.enums.item_type import ItemType


class LootSystem:
    """
    Central registry for loot drops and item lookups.

    Parameters
    ----------
    item_catalogue:
        Mapping of item_id → ``Item`` instances loaded at boot.
    loot_tables:
        Mapping of mob_template_id → list of loot-table rows.
    mob_templates:
        Mapping of mob_template_id → mob template dicts (for money).
    """

    def __init__(
        self,
        item_catalogue: dict[str, Item],
        loot_tables: dict[str, list[dict]],
        mob_templates: dict[str, dict],
    ) -> None:
        self._items = item_catalogue
        self._tables = loot_tables
        self._templates = mob_templates
        self._drops: dict[str, LootDrop] = {}

    # -- read-only -----------------------------------------------------------

    def get_drop(self, drop_id: str) -> Optional[LootDrop]:
        """Return the active loot drop, or ``None``."""
        drop = self._drops.get(drop_id)
        if drop and not drop.is_active:
            del self._drops[drop_id]
            return None
        return drop

    def get_drops_at(self, x: float, y: float, radius: float = 30.0) -> list[LootDrop]:
        """Return active drops within *radius* of (x, y)."""
        result = []
        for drop in list(self._drops.values()):
            if not drop.is_active:
                continue
            dx = drop.position[0] - x
            dy = drop.position[1] - y
            if (dx * dx + dy * dy) <= radius * radius:
                result.append(drop)
        return result

    def get_item(self, item_id: str) -> Optional[Item]:
        """Look up an item from the catalogue."""
        return self._items.get(item_id)

    # -- drop lifecycle ------------------------------------------------------

    def generate_drop(
        self,
        mob_id: str,
        position_x: float,
        position_y: float,
    ) -> Optional[LootDrop]:
        """
        Roll the loot table for *mob_id* and create a drop.

        Returns ``None`` if the mob has no loot table and no money range,
        or if nothing was rolled.
        """
        table_rows = self._tables.get(mob_id, [])
        template = self._templates.get(mob_id, {})

        rolled_items: list[Item] = []
        for row in table_rows:
            if random.random() <= row["drop_chance"]:
                item = self._items.get(row["item_id"])
                if item is None:
                    continue
                qty = random.randint(
                    row.get("min_quantity", 1),
                    row.get("max_quantity", 1),
                )
                for _ in range(qty):
                    rolled_items.append(item)

        money_min = template.get("drop_money_min", 0)
        money_max = template.get("drop_money_max", 0)
        money = random.randint(money_min, money_max) if money_max > 0 else 0

        if not rolled_items and money == 0:
            return None

        drop_id = f"{mob_id}_loot"
        drop = LootDrop(
            drop_id=drop_id,
            mob_id=mob_id,
            position_x=position_x,
            position_y=position_y,
            items=rolled_items,
            money=money,
        )
        self._drops[drop_id] = drop
        return drop

    def invalidate_mob_drops(self, mob_id: str) -> None:
        """
        Invalidate all drops belonging to *mob_id*.

        Called when the mob respawns so players can no longer loot.
        """
        drop_id = f"{mob_id}_loot"
        drop = self._drops.get(drop_id)
        if drop:
            drop.invalidate()
            del self._drops[drop_id]

    def remove_empty_drops(self) -> None:
        """Garbage-collect drops that have been fully looted."""
        to_remove = [
            did for did, d in self._drops.items()
            if d.is_empty or not d.is_active
        ]
        for did in to_remove:
            del self._drops[did]

    # -- all active drops for world state ------------------------------------

    def get_all_active_drops(self) -> list[LootDrop]:
        """Return every currently lootable drop."""
        return [d for d in self._drops.values() if d.is_active]

    # -- factory helper ------------------------------------------------------

    @staticmethod
    def build_item_catalogue(item_rows: list[dict]) -> dict[str, Item]:
        """
        Convert database rows into ``Item`` instances.

        Parameters
        ----------
        item_rows:
            List of dicts from ``ItemRepository.load_all()``.
        """
        catalogue: dict[str, Item] = {}
        for row in item_rows:
            catalogue[row["id"]] = Item(
                item_id=row["id"],
                name=row["name"],
                item_type=ItemType(row.get("item_type", "junk")),
                sell_value=row.get("sell_value", 0),
                slot=ItemSlot(row.get("slot", "none")),
                stat_bonuses=row.get("stat_bonuses", {}),
                description=row.get("description", ""),
                stackable=bool(row.get("stackable", False)),
                max_stack=row.get("max_stack", 1),
                level_req=row.get("level_req", 1),
            )
        return catalogue

    @staticmethod
    def build_loot_tables(
        mob_ids: list[str],
        loot_repo,
    ) -> dict[str, list[dict]]:
        """
        Load loot tables for every mob template.

        Parameters
        ----------
        mob_ids:
            List of mob template ids to look up.
        loot_repo:
            ``LootTableRepository`` instance.
        """
        tables: dict[str, list[dict]] = {}
        for mid in mob_ids:
            rows = loot_repo.load_by_mob(mid)
            if rows:
                tables[mid] = rows
        return tables