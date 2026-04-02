# game/db/schema.py
"""SQL table definitions for the game database."""

ZONES_TABLE = """
CREATE TABLE IF NOT EXISTS zones (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    chunk_size  INTEGER NOT NULL DEFAULT 100,
    min_x       REAL NOT NULL,
    min_y       REAL NOT NULL,
    max_x       REAL NOT NULL,
    max_y       REAL NOT NULL
);
"""

PLAYERS_TABLE = """
CREATE TABLE IF NOT EXISTS players (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    race        TEXT NOT NULL,
    class       TEXT NOT NULL,
    level       INTEGER NOT NULL DEFAULT 1,
    health      INTEGER NOT NULL DEFAULT 100,
    mana        INTEGER NOT NULL DEFAULT 200,
    position_x  REAL NOT NULL DEFAULT 0.0,
    position_y  REAL NOT NULL DEFAULT 0.0,
    copper      INTEGER NOT NULL DEFAULT 0,
    stats_json  TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

MOB_TEMPLATES_TABLE = """
CREATE TABLE IF NOT EXISTS mob_templates (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    class            TEXT NOT NULL,
    level            INTEGER NOT NULL DEFAULT 1,
    base_health      INTEGER NOT NULL DEFAULT 100,
    base_mana        INTEGER NOT NULL DEFAULT 0,
    spawn_x          REAL NOT NULL,
    spawn_y          REAL NOT NULL,
    zone_id          TEXT NOT NULL,
    respawn_sec      INTEGER NOT NULL DEFAULT 60,
    aggression_type  TEXT NOT NULL DEFAULT 'passive',
    aggro_range      REAL NOT NULL DEFAULT 80.0,
    attack_range     REAL NOT NULL DEFAULT 5.0,
    leash_range      REAL NOT NULL DEFAULT 200.0,
    patrol_radius    REAL NOT NULL DEFAULT 30.0,
    move_speed       REAL NOT NULL DEFAULT 40.0,
    attack_cooldown  REAL NOT NULL DEFAULT 2.0,
    drop_money_min   INTEGER NOT NULL DEFAULT 0,
    drop_money_max   INTEGER NOT NULL DEFAULT 0,
    is_quest_giver   INTEGER NOT NULL DEFAULT 0,
    is_vendor        INTEGER NOT NULL DEFAULT 0,
    stats_json       TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (zone_id) REFERENCES zones(id)
);
"""

ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS items (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    item_type     TEXT NOT NULL DEFAULT 'junk',
    sell_value    INTEGER NOT NULL DEFAULT 0,
    slot          TEXT NOT NULL DEFAULT 'none',
    stat_bonuses  TEXT NOT NULL DEFAULT '{}',
    description   TEXT NOT NULL DEFAULT '',
    stackable     INTEGER NOT NULL DEFAULT 0,
    max_stack     INTEGER NOT NULL DEFAULT 1,
    level_req     INTEGER NOT NULL DEFAULT 1
);
"""

LOOT_TABLES_TABLE = """
CREATE TABLE IF NOT EXISTS loot_tables (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    mob_template_id  TEXT NOT NULL,
    item_id          TEXT NOT NULL,
    drop_chance      REAL NOT NULL DEFAULT 0.0,
    min_quantity     INTEGER NOT NULL DEFAULT 1,
    max_quantity     INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (mob_template_id) REFERENCES mob_templates(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);
"""

QUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS quests (
    id               TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    description      TEXT NOT NULL,
    giver_entity_id  TEXT NOT NULL,
    level_req        INTEGER NOT NULL DEFAULT 1,
    reward_copper    INTEGER NOT NULL DEFAULT 0,
    reward_xp        INTEGER NOT NULL DEFAULT 0,
    reward_items     TEXT NOT NULL DEFAULT '[]',
    repeatable       INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (giver_entity_id) REFERENCES mob_templates(id)
);
"""

QUEST_OBJECTIVES_TABLE = """
CREATE TABLE IF NOT EXISTS quest_objectives (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id         TEXT NOT NULL,
    objective_id     TEXT NOT NULL,
    description      TEXT NOT NULL,
    target_id        TEXT NOT NULL,
    required_count   INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (quest_id) REFERENCES quests(id)
);
"""

VENDOR_STOCK_TABLE = """
CREATE TABLE IF NOT EXISTS vendor_stock (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id        TEXT NOT NULL,
    item_id          TEXT NOT NULL,
    quantity         INTEGER NOT NULL DEFAULT -1,
    buy_price        INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (vendor_id) REFERENCES mob_templates(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);
"""

ALL_TABLES = [
    ZONES_TABLE,
    PLAYERS_TABLE,
    MOB_TEMPLATES_TABLE,
    ITEMS_TABLE,
    LOOT_TABLES_TABLE,
    QUESTS_TABLE,
    QUEST_OBJECTIVES_TABLE,
    VENDOR_STOCK_TABLE,
]