# game/db/schema.py
"""SQL table definitions for the game database."""

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
    stats_json  TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

MOB_TEMPLATES_TABLE = """
CREATE TABLE IF NOT EXISTS mob_templates (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    class        TEXT NOT NULL,
    level        INTEGER NOT NULL DEFAULT 1,
    base_health  INTEGER NOT NULL DEFAULT 100,
    base_mana    INTEGER NOT NULL DEFAULT 0,
    spawn_x      REAL NOT NULL,
    spawn_y      REAL NOT NULL,
    zone_id      TEXT NOT NULL,
    respawn_sec  INTEGER NOT NULL DEFAULT 60,
    stats_json   TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (zone_id) REFERENCES zones(id)
);
"""

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

LOOT_TABLES_TABLE = """
CREATE TABLE IF NOT EXISTS loot_tables (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    mob_template_id  TEXT NOT NULL,
    item_name        TEXT NOT NULL,
    drop_chance      REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (mob_template_id) REFERENCES mob_templates(id)
);
"""

ALL_TABLES = [
    ZONES_TABLE,
    PLAYERS_TABLE,
    MOB_TEMPLATES_TABLE,
    LOOT_TABLES_TABLE,
]