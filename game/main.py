# game/main.py
"""
Terminal entry point for the game server.

Bootstraps the database, loads zones and mob templates,
wires up all systems, and runs an interactive command loop
that simulates client inputs against the real server logic.
"""

from __future__ import annotations

from game.characters.character import Character
from game.core.event_bus import EventBus
from game.core.game_loop import GameLoop
from game.db.database import Database
from game.db.repositories.mob_template_repo import MobTemplateRepository
from game.db.repositories.player_repo import PlayerRepository
from game.db.repositories.zone_repo import ZoneRepository
from game.definitions import get_class_definition
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.network.connection import Connection
from game.network.connection_manager import ConnectionManager
from game.network.message import Message
from game.network.message_type import MessageType
from game.systems.combat_system import AttackIntent, CombatSystem
from game.systems.movement_system import MoveIntent, MovementSystem
from game.systems.spawn_system import SpawnSystem
from game.systems.sync_system import SyncSystem
from game.world.world import World
from game.world.zone import Zone, ZoneBounds


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


def _seed_mobs(repo: MobTemplateRepository) -> None:
    """Insert starter mob templates if empty."""
    if repo.load_by_zone("elwynn_forest"):
        return
    templates = [
        {"id": "wolf_01", "name": "Forest Wolf", "class": "WARRIOR",
         "level": 2, "base_health": 60, "base_mana": 0,
         "spawn_x": 150.0, "spawn_y": 150.0,
         "zone_id": "elwynn_forest", "respawn_sec": 30, "stats_json": {}},
        {"id": "bandit_01", "name": "Defias Bandit", "class": "ROGUE",
         "level": 3, "base_health": 80, "base_mana": 0,
         "spawn_x": 250.0, "spawn_y": 300.0,
         "zone_id": "elwynn_forest", "respawn_sec": 45, "stats_json": {}},
        {"id": "kobold_01", "name": "Kobold Miner", "class": "WARRIOR",
         "level": 1, "base_health": 40, "base_mana": 0,
         "spawn_x": 350.0, "spawn_y": 200.0,
         "zone_id": "elwynn_forest", "respawn_sec": 20, "stats_json": {}},
    ]
    for t in templates:
        repo.save(t)


# ── server bootstrap ───────────────────────────────────────────────

def _build_server() -> dict:
    """
    Construct and wire every server component.

    Returns a dict of named references for the terminal loop.
    """
    db = Database(":memory:")
    db.connect()

    zone_repo = ZoneRepository(db)
    mob_repo = MobTemplateRepository(db)
    player_repo = PlayerRepository(db)

    _seed_zones(zone_repo)
    _seed_mobs(mob_repo)

    event_bus = EventBus()
    world = World()
    connections = ConnectionManager()

    for row in zone_repo.list_all():
        zone = Zone(
            zone_id=row["id"],
            name=row["name"],
            bounds=ZoneBounds(row["min_x"], row["min_y"],
                              row["max_x"], row["max_y"]),
            chunk_size=row["chunk_size"],
        )
        world.add_zone(zone)

    movement = MovementSystem(world, event_bus)
    combat = CombatSystem(world, event_bus)
    spawn = SpawnSystem(world, event_bus)
    sync = SyncSystem(world, event_bus, connections)

    for t in mob_repo.load_by_zone("elwynn_forest"):
        spawn.register_template(t)

    game_loop = GameLoop(tick_rate=20)
    game_loop.register_system(movement)
    game_loop.register_system(combat)
    game_loop.register_system(spawn)
    game_loop.register_system(sync)

    return {
        "db": db,
        "player_repo": player_repo,
        "world": world,
        "connections": connections,
        "movement": movement,
        "combat": combat,
        "game_loop": game_loop,
        "event_bus": event_bus,
    }


# ── player connection helper ───────────────────────────────────────

def _connect_player(srv: dict, player_id: str, name: str,
                    race: Race, class_type: CharacterClassType,
                    x: float, y: float) -> None:
    """Simulate a player connecting and entering the world."""
    class_def = get_class_definition(class_type)
    character = Character(
        name=player_id, race=race, class_def=class_def,
        level=1, base_health=100,
    )
    zone_id = srv["world"].add_entity(character, x, y)
    conn = Connection(player_id)
    srv["connections"].add(conn)

    srv["player_repo"].save({
        "id": player_id, "name": name,
        "race": race.value, "class": class_type.value,
        "level": 1, "health": 100, "mana": 200,
        "position_x": x, "position_y": y, "stats_json": {},
    })

    conn.send(Message(MessageType.S_WELCOME, {"player_id": player_id}))
    conn.send(Message(MessageType.S_CHARACTER_DATA, {
        "name": name, "race": race.value,
        "class": class_type.value, "level": 1,
        "health": 100, "x": x, "y": y,
    }))

    if zone_id:
        zone = srv["world"].get_zone(zone_id)
        conn.send(Message(MessageType.S_ZONE_ENTERED, {
            "zone_id": zone_id,
            "zone_name": zone.name if zone else "",
        }))
        print(f"  [{player_id}] entered zone '{zone_id}'")
    else:
        conn.send(Message(MessageType.S_OUTSIDE_ZONE, {
            "message": "You are outside the gaming zone.",
        }))
        print(f"  [{player_id}] is OUTSIDE all gaming zones")


# ── terminal command loop ──────────────────────────────────────────

def _print_help() -> None:
    print("""
Commands:
  connect <id> <name> <race> <class> <x> <y>  — join the server
  move <id> <x> <y>                            — move a player
  attack <attacker_id> <target_id>             — attack an entity
  tick                                         — advance one server tick
  status <id>                                  — show entity info
  nearby <id>                                  — list nearby entities
  zones                                        — list all zones
  quit                                         — shut down

Races:   Human, Dwarf, Night Elf, Gnome, Orc, Tauren, Troll, Undead
Classes: Hunter, Mage, Druid, Paladin, Priest, Rogue, Shaman, Warlock, Warrior
""")


def run() -> None:
    """Boot the server and enter the interactive command loop."""
    print("=" * 55)
    print("  GAME SERVER — terminal simulation")
    print("=" * 55)

    srv = _build_server()
    print("\nServer ready. Type 'help' for commands.\n")

    dt = 0.05

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd == "help":
            _print_help()

        elif cmd == "connect" and len(parts) >= 7:
            try:
                race = Race(parts[3])
                cls = CharacterClassType(parts[4])
                _connect_player(
                    srv, parts[1], parts[2], race, cls,
                    float(parts[5]), float(parts[6]),
                )
            except (ValueError, KeyError) as e:
                print(f"  Error: {e}")

        elif cmd == "move" and len(parts) >= 4:
            srv["movement"].enqueue(
                MoveIntent(parts[1], float(parts[2]), float(parts[3]))
            )
            srv["game_loop"].tick_once(dt)

        elif cmd == "attack" and len(parts) >= 3:
            srv["combat"].enqueue(AttackIntent(parts[1], parts[2]))
            srv["game_loop"].tick_once(dt)

        elif cmd == "tick":
            srv["game_loop"].tick_once(dt)
            print(f"  Tick #{srv['game_loop'].tick_count}")

        elif cmd == "status" and len(parts) >= 2:
            eid = parts[1]
            entity = srv["world"].get_entity(eid)
            pos = srv["world"].get_entity_position(eid)
            zone_id = srv["world"].get_entity_zone_id(eid)
            if entity:
                print(f"  {entity}")
                print(f"  Position: {pos}")
                print(f"  Zone: {zone_id or 'OUTSIDE'}")
                print(f"  Health: {entity.health.current}/{entity.health.maximum}")
            else:
                print(f"  Entity '{eid}' not found.")

        elif cmd == "nearby" and len(parts) >= 2:
            ids = srv["world"].get_nearby_entity_ids(parts[1])
            if ids:
                for nid in sorted(ids):
                    e = srv["world"].get_entity(nid)
                    p = srv["world"].get_entity_position(nid)
                    print(f"  {nid}: {p}  hp={e.health.current if e else '?'}")
            else:
                print("  No nearby entities (outside zone or alone).")

        elif cmd == "zones":
            for z in srv["world"].get_all_zones():
                b = z.bounds
                print(f"  {z.zone_id}: '{z.name}' "
                      f"[{b.min_x},{b.min_y} -> {b.max_x},{b.max_y}]")

        elif cmd == "quit":
            break

        else:
            print("  Unknown command. Type 'help'.")

    srv["db"].close()
    print("\nServer shut down.")


if __name__ == "__main__":
    run()