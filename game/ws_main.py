# game/ws_main.py
"""
Entry point for the WebSocket game server.

Boots the game infrastructure (database, zones, mobs, items,
quests, loot tables, vendors) and exposes it over WebSockets.

Usage::

    python -m game.ws_main
"""

from __future__ import annotations

import asyncio
import logging
import sys

from game.core.event_bus import EventBus
from game.db.database import Database
from game.db.repositories.item_repo import ItemRepository
from game.db.repositories.loot_table_repo import LootTableRepository
from game.db.repositories.mob_template_repo import MobTemplateRepository
from game.db.repositories.quest_repo import QuestRepository
from game.db.repositories.vendor_repo import VendorRepository
from game.db.repositories.zone_repo import ZoneRepository
from game.network.connection_manager import ConnectionManager
from game.network.ws_bridge import WSBridge
from game.network.ws_server import WSServer
from game.systems.combat_system import CombatSystem
from game.systems.loot_system import LootSystem
from game.systems.movement_system import MovementSystem
from game.systems.quest_system import QuestSystem
from game.systems.sync_system import SyncSystem
from game.systems.vendor_system import VendorSystem
from game.world.mob_instance import MobInstance
from game.world.world import World
from game.world.zone import Zone, ZoneBounds
from game.world.zone_controller import ZoneController

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── database seeding ───────────────────────────────────────────────

def _seed_zones(repo: ZoneRepository) -> None:
    """Insert a starter zone if the table is empty."""
    if repo.list_all():
        return
    repo.save({
        "id": "elwynn_forest",
        "name": "Elwynn Forest",
        "chunk_size": 100,
        "min_x": 0.0, "min_y": 0.0,
        "max_x": 500.0, "max_y": 500.0,
    })


def _seed_items(repo: ItemRepository) -> None:
    """Insert starter item definitions."""
    if repo.load_all():
        return
    items = [
        {
            "id": "wolf_pelt", "name": "Wolf Pelt",
            "item_type": "junk", "sell_value": 25,
            "description": "A rough pelt from a forest wolf. Sells for a few copper.",
        },
        {
            "id": "wolf_fang", "name": "Wolf Fang",
            "item_type": "junk", "sell_value": 15,
            "description": "A sharp canine tooth. Troll alchemists covet these.",
        },
        {
            "id": "bandit_bandana", "name": "Red Bandana",
            "item_type": "armor", "sell_value": 50,
            "slot": "head",
            "stat_bonuses": {"Agility": 1},
            "description": "A crimson bandana once worn by a Defias outlaw.",
            "level_req": 1,
        },
        {
            "id": "rusty_dagger", "name": "Rusty Dagger",
            "item_type": "weapon", "sell_value": 75,
            "slot": "main_hand",
            "stat_bonuses": {"Strength": 2},
            "description": "A battered dagger. Still sharp enough to cut.",
            "level_req": 1,
        },
        {
            "id": "deer_meat", "name": "Deer Meat",
            "item_type": "consumable", "sell_value": 10,
            "description": "Restores health when consumed.",
            "stackable": True, "max_stack": 10,
        },
        {
            "id": "healing_potion", "name": "Minor Healing Potion",
            "item_type": "consumable", "sell_value": 30,
            "description": "Restores a small amount of health.",
            "stackable": True, "max_stack": 5,
        },
        # ── Vendor-sold items ──────────────────────────────────────
        {
            "id": "bread", "name": "Freshly Baked Bread",
            "item_type": "consumable", "sell_value": 5,
            "description": "A warm loaf of bread. Restores a small amount of health.",
            "stackable": True, "max_stack": 20,
        },
        {
            "id": "water_skin", "name": "Refreshing Water",
            "item_type": "consumable", "sell_value": 5,
            "description": "A skin of clean water from Crystal Lake.",
            "stackable": True, "max_stack": 20,
        },
        {
            "id": "linen_bandage", "name": "Linen Bandage",
            "item_type": "consumable", "sell_value": 15,
            "description": "A simple bandage. Slowly restores health.",
            "stackable": True, "max_stack": 10,
        },
        {
            "id": "short_sword", "name": "Short Sword",
            "item_type": "weapon", "sell_value": 100,
            "slot": "main_hand",
            "stat_bonuses": {"Strength": 3},
            "description": "A reliable blade forged in Stormwind.",
            "level_req": 1,
        },
        {
            "id": "apprentice_robe", "name": "Apprentice's Robe",
            "item_type": "armor", "sell_value": 80,
            "slot": "chest",
            "stat_bonuses": {"Intellect": 2},
            "description": "A plain cloth robe suitable for novice spellcasters.",
            "level_req": 1,
        },
        {
            "id": "leather_boots", "name": "Sturdy Leather Boots",
            "item_type": "armor", "sell_value": 60,
            "slot": "feet",
            "stat_bonuses": {"Agility": 1, "Stamina": 1},
            "description": "Well-worn boots that have walked many roads.",
            "level_req": 1,
        },
    ]
    for item in items:
        repo.save(item)


def _seed_mobs(repo: MobTemplateRepository) -> None:
    """Insert starter mob templates with AI configuration."""
    if repo.load_by_zone("elwynn_forest"):
        return
    templates = [
        {
            "id": "wolf_01", "name": "Forest Wolf",
            "class": "WARRIOR", "level": 2,
            "base_health": 60, "base_mana": 0,
            "spawn_x": 150.0, "spawn_y": 150.0,
            "zone_id": "elwynn_forest", "respawn_sec": 15,
            "aggression_type": "aggressive",
            "aggro_range": 60.0, "attack_range": 5.0,
            "leash_range": 150.0, "patrol_radius": 25.0,
            "move_speed": 45.0, "attack_cooldown": 1.5,
            "drop_money_min": 2, "drop_money_max": 8,
            "stats_json": {},
        },
        {
            "id": "bandit_01", "name": "Defias Bandit",
            "class": "ROGUE", "level": 3,
            "base_health": 80, "base_mana": 0,
            "spawn_x": 250.0, "spawn_y": 300.0,
            "zone_id": "elwynn_forest", "respawn_sec": 20,
            "aggression_type": "aggressive",
            "aggro_range": 50.0, "attack_range": 5.0,
            "leash_range": 120.0, "patrol_radius": 20.0,
            "move_speed": 35.0, "attack_cooldown": 2.0,
            "drop_money_min": 5, "drop_money_max": 15,
            "stats_json": {},
        },
        {
            "id": "deer_01", "name": "Young Deer",
            "class": "WARRIOR", "level": 1,
            "base_health": 30, "base_mana": 0,
            "spawn_x": 350.0, "spawn_y": 200.0,
            "zone_id": "elwynn_forest", "respawn_sec": 10,
            "aggression_type": "passive",
            "aggro_range": 0.0, "attack_range": 5.0,
            "leash_range": 100.0, "patrol_radius": 40.0,
            "move_speed": 50.0, "attack_cooldown": 3.0,
            "drop_money_min": 0, "drop_money_max": 2,
            "stats_json": {},
        },
        {
            "id": "marshal_dughan", "name": "Marshal Dughan",
            "class": "WARRIOR", "level": 10,
            "base_health": 500, "base_mana": 0,
            "spawn_x": 245.0, "spawn_y": 255.0,
            "zone_id": "elwynn_forest", "respawn_sec": 5,
            "aggression_type": "passive",
            "aggro_range": 0.0, "attack_range": 5.0,
            "leash_range": 10.0, "patrol_radius": 3.0,
            "move_speed": 0.0, "attack_cooldown": 999.0,
            "is_quest_giver": True,
            "stats_json": {},
        },
        # ── Vendor NPC ────────────────────────────────────────────
        {
            "id": "tomas_vendor", "name": "Tomas the Merchant",
            "class": "WARRIOR", "level": 10,
            "base_health": 500, "base_mana": 0,
            "spawn_x": 260.0, "spawn_y": 230.0,
            "zone_id": "elwynn_forest", "respawn_sec": 5,
            "aggression_type": "passive",
            "aggro_range": 0.0, "attack_range": 5.0,
            "leash_range": 10.0, "patrol_radius": 3.0,
            "move_speed": 0.0, "attack_cooldown": 999.0,
            "is_vendor": True,
            "stats_json": {},
        },
    ]
    for t in templates:
        repo.save(t)


def _seed_loot_tables(loot_repo: LootTableRepository) -> None:
    """Insert starter loot table entries."""
    if loot_repo.load_by_mob("wolf_01"):
        return
    loot_repo.save("wolf_01", "wolf_pelt", 0.6)
    loot_repo.save("wolf_01", "wolf_fang", 0.3)
    loot_repo.save("bandit_01", "bandit_bandana", 0.25)
    loot_repo.save("bandit_01", "rusty_dagger", 0.15)
    loot_repo.save("deer_01", "deer_meat", 0.8)


def _seed_quests(quest_repo: QuestRepository) -> None:
    """Insert starter quest definitions."""
    existing = quest_repo.load_all()
    if existing:
        return

    quest_repo.save_quest({
        "id": "wolves_of_elwynn",
        "title": "The Wolves of Elwynn",
        "description": (
            "Marshal Dughan paces behind his desk, his brow furrowed. "
            "\"The wolves in this forest have grown bolder. Farmers report "
            "attacks on their livestock nightly. I need someone to thin "
            "their numbers. Bring me proof that you've dealt with at least "
            "three of the beasts, and I'll see you're rewarded.\""
        ),
        "giver_entity_id": "marshal_dughan",
        "level_req": 1,
        "reward_copper": 50,
        "reward_xp": 100,
        "reward_items": ["healing_potion"],
    })
    quest_repo.save_objective({
        "quest_id": "wolves_of_elwynn",
        "objective_id": "kill_wolves",
        "description": "Slay Forest Wolves",
        "target_id": "wolf_01",
        "required_count": 3,
    })

    quest_repo.save_quest({
        "id": "defias_menace",
        "title": "The Defias Menace",
        "description": (
            "\"These Defias thugs are becoming a real problem. They've "
            "been harassing travelers along the road to Goldshire. "
            "Put an end to their leader — or at least thin their ranks. "
            "The people of Elwynn will thank you.\""
        ),
        "giver_entity_id": "marshal_dughan",
        "level_req": 1,
        "reward_copper": 100,
        "reward_xp": 200,
        "reward_items": ["rusty_dagger"],
    })
    quest_repo.save_objective({
        "quest_id": "defias_menace",
        "objective_id": "kill_bandits",
        "description": "Defeat Defias Bandits",
        "target_id": "bandit_01",
        "required_count": 2,
    })


def _seed_vendor_stock(vendor_repo: VendorRepository) -> None:
    """Insert starter vendor stock entries."""
    if vendor_repo.load_all():
        return
    vendor_repo.save("tomas_vendor", "bread", -1, 10)
    vendor_repo.save("tomas_vendor", "water_skin", -1, 10)
    vendor_repo.save("tomas_vendor", "linen_bandage", 10, 50)
    vendor_repo.save("tomas_vendor", "healing_potion", 5, 100)
    vendor_repo.save("tomas_vendor", "short_sword", 3, 250)
    vendor_repo.save("tomas_vendor", "apprentice_robe", 2, 200)
    vendor_repo.save("tomas_vendor", "leather_boots", 3, 150)


# ── server bootstrap ───────────────────────────────────────────────

def build_server() -> dict:
    """
    Construct every server component and start zone controllers.

    Returns a dict of named references for the WebSocket layer.
    """
    db = Database(":memory:")
    db.connect()

    zone_repo = ZoneRepository(db)
    mob_repo = MobTemplateRepository(db)
    item_repo = ItemRepository(db)
    loot_repo = LootTableRepository(db)
    quest_repo = QuestRepository(db)
    vendor_repo = VendorRepository(db)

    _seed_zones(zone_repo)
    _seed_items(item_repo)
    _seed_mobs(mob_repo)
    _seed_loot_tables(loot_repo)
    _seed_quests(quest_repo)
    _seed_vendor_stock(vendor_repo)

    event_bus = EventBus()
    world = World()
    connections = ConnectionManager()

    movement = MovementSystem(world, event_bus)
    combat = CombatSystem(world, event_bus, base_damage=15)
    sync = SyncSystem(world, event_bus, connections)

    # Build item catalogue and loot tables
    item_catalogue = LootSystem.build_item_catalogue(item_repo.load_all())
    all_mob_rows = []
    mob_templates_map: dict[str, dict] = {}
    for zrow in zone_repo.list_all():
        rows = mob_repo.load_by_zone(zrow["id"])
        for r in rows:
            all_mob_rows.append(r)
            mob_templates_map[r["id"]] = r

    loot_tables = LootSystem.build_loot_tables(
        [r["id"] for r in all_mob_rows], loot_repo
    )
    loot_system = LootSystem(item_catalogue, loot_tables, mob_templates_map)

    # Build quest system
    quest_system = QuestSystem.build_from_db_rows(
        quest_repo.load_all(), item_catalogue
    )

    # Build vendor system
    vendor_system = VendorSystem(item_catalogue)
    for mob_row in all_mob_rows:
        if mob_row.get("is_vendor", False):
            vendor_inv = vendor_system.register_vendor(
                mob_row["id"], starting_copper=5000
            )
            stock_rows = vendor_repo.load_by_vendor(mob_row["id"])
            for sr in stock_rows:
                item = item_catalogue.get(sr["item_id"])
                if item:
                    from game.components.vendor_stock import VendorStockEntry
                    vendor_inv.add_stock(VendorStockEntry(
                        item=item,
                        quantity=sr["quantity"],
                        buy_price=sr["buy_price"],
                    ))

    controllers: dict[str, ZoneController] = {}

    for row in zone_repo.list_all():
        zone = Zone(
            zone_id=row["id"],
            name=row["name"],
            bounds=ZoneBounds(
                row["min_x"], row["min_y"],
                row["max_x"], row["max_y"],
            ),
            chunk_size=row["chunk_size"],
        )
        world.add_zone(zone)

        controller = ZoneController(
            zone=zone, world=world, event_bus=event_bus,
            connections=connections, movement=movement,
            combat=combat, sync=sync, tick_rate=20,
        )

        for t in mob_repo.load_by_zone(zone.zone_id):
            mob = MobInstance.from_template(t)
            controller.register_mob(mob)

        controllers[zone.zone_id] = controller

    return {
        "db": db,
        "world": world,
        "event_bus": event_bus,
        "connections": connections,
        "movement": movement,
        "combat": combat,
        "controllers": controllers,
        "loot_system": loot_system,
        "quest_system": quest_system,
        "vendor_system": vendor_system,
    }


# ── main ───────────────────────────────────────────────────────────

def run(host: str = "0.0.0.0", port: int = 8765) -> None:
    """Boot the game engine and WebSocket server."""
    logger.info("Building game server...")
    srv = build_server()

    for zid, ctrl in srv["controllers"].items():
        ctrl.start()
        logger.info(
            "Zone '%s' controller started (%d mobs)", zid, ctrl.mob_count
        )

    bridge = WSBridge(
        world=srv["world"],
        event_bus=srv["event_bus"],
        connections=srv["connections"],
        movement=srv["movement"],
        combat=srv["combat"],
        controllers=srv["controllers"],
        loot_system=srv["loot_system"],
        quest_system=srv["quest_system"],
        vendor_system=srv["vendor_system"],
    )

    ws_server = WSServer(bridge, host=host, port=port)

    logger.info("Starting WebSocket server on ws://%s:%d ...", host, port)
    try:
        asyncio.run(ws_server.start())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        for ctrl in srv["controllers"].values():
            ctrl.stop()
        srv["db"].close()
        logger.info("Server shut down.")


if __name__ == "__main__":
    run()