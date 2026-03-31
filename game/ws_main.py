# game/ws_main.py
"""
Entry point for the WebSocket game server.

Boots the same game infrastructure as ``game.main`` (database,
zones, mob templates, zone controllers) but exposes it over
WebSockets instead of a terminal interface.

Usage::

    python -m game.ws_main

The server listens on ``ws://0.0.0.0:8765`` by default.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from game.core.event_bus import EventBus
from game.db.database import Database
from game.db.repositories.mob_template_repo import MobTemplateRepository
from game.db.repositories.zone_repo import ZoneRepository
from game.network.connection_manager import ConnectionManager
from game.network.ws_bridge import WSBridge
from game.network.ws_server import WSServer
from game.systems.combat_system import CombatSystem
from game.systems.movement_system import MovementSystem
from game.systems.sync_system import SyncSystem
from game.world.mob_instance import MobInstance
from game.world.world import World
from game.world.zone import Zone, ZoneBounds
from game.world.zone_controller import ZoneController

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── database seeding (identical to game.main) ──────────────────────

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
            "stats_json": {},
        },
    ]
    for t in templates:
        repo.save(t)


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

    _seed_zones(zone_repo)
    _seed_mobs(mob_repo)

    event_bus = EventBus()
    world = World()
    connections = ConnectionManager()

    movement = MovementSystem(world, event_bus)
    combat = CombatSystem(world, event_bus, base_damage=15)
    sync = SyncSystem(world, event_bus, connections)

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