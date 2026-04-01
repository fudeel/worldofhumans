# game/main.py
"""
Terminal entry point for the game server.

Boots the database, seeds zones, mob templates, and map objects,
then starts a ``ZoneController`` per zone in background threads.
The world is now alive — mobs patrol, chase, and attack on their
own while map objects sit ready for interaction.

The terminal provides commands to connect players, move them
into zones, interact with map objects, and watch the zone react
in real time.
"""

from __future__ import annotations

import time

from game.characters.character import Character
from game.components.vector2 import Vector2
from game.core.event_bus import EventBus
from game.db.database import Database
from game.db.repositories.map_object_repo import MapObjectRepository
from game.db.repositories.mob_template_repo import MobTemplateRepository
from game.db.repositories.player_repo import PlayerRepository
from game.db.repositories.zone_repo import ZoneRepository
from game.definitions import get_class_definition
from game.enums.character_class_type import CharacterClassType
from game.enums.mob_state import MobState
from game.enums.race import Race
from game.network.connection import Connection
from game.network.connection_manager import ConnectionManager
from game.network.message import Message
from game.network.message_type import MessageType
from game.systems.combat_system import AttackIntent, CombatSystem
from game.systems.interaction_system import InteractionSystem
from game.systems.movement_system import MoveIntent, MovementSystem
from game.systems.sync_system import SyncSystem
from game.world.map_object_factory import MapObjectFactory
from game.world.mob_instance import MobInstance
from game.world.world import World
from game.world.zone import Zone, ZoneBounds
from game.world.zone_controller import ZoneController


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


def _seed_map_objects(repo: MapObjectRepository) -> None:
    """Insert starter map objects for Elwynn Forest."""
    if repo.load_by_zone("elwynn_forest"):
        return
    objects = [
        {
            "id": "chest_01",
            "name": "Weathered Chest",
            "object_type": "interactable",
            "interaction": "activate",
            "zone_id": "elwynn_forest",
            "spawn_x": 200.0, "spawn_y": 180.0,
            "interact_range": 8.0,
            "respawn_sec": 120.0,
            "metadata": {"loot_table": "common_chest"},
        },
        {
            "id": "herb_01",
            "name": "Peacebloom",
            "object_type": "resource_node",
            "interaction": "gather",
            "zone_id": "elwynn_forest",
            "spawn_x": 100.0, "spawn_y": 250.0,
            "interact_range": 6.0,
            "respawn_sec": 60.0,
            "metadata": {"skill_required": "Herbalism", "skill_level": 1},
        },
        {
            "id": "herb_02",
            "name": "Silverleaf",
            "object_type": "resource_node",
            "interaction": "gather",
            "zone_id": "elwynn_forest",
            "spawn_x": 420.0, "spawn_y": 380.0,
            "interact_range": 6.0,
            "respawn_sec": 60.0,
            "metadata": {"skill_required": "Herbalism", "skill_level": 1},
        },
        {
            "id": "ore_01",
            "name": "Copper Vein",
            "object_type": "resource_node",
            "interaction": "gather",
            "zone_id": "elwynn_forest",
            "spawn_x": 380.0, "spawn_y": 120.0,
            "interact_range": 6.0,
            "respawn_sec": 90.0,
            "metadata": {"skill_required": "Mining", "skill_level": 1},
        },
        {
            "id": "npc_marshal",
            "name": "Marshal McBride",
            "object_type": "npc",
            "interaction": "talk",
            "zone_id": "elwynn_forest",
            "spawn_x": 250.0, "spawn_y": 250.0,
            "interact_range": 10.0,
            "respawn_sec": 0.0,
            "metadata": {"role": "quest_giver", "title": "Human Starting Zone"},
        },
        {
            "id": "item_sword",
            "name": "Rusty Shortsword",
            "object_type": "item",
            "interaction": "loot",
            "zone_id": "elwynn_forest",
            "spawn_x": 310.0, "spawn_y": 160.0,
            "interact_range": 5.0,
            "respawn_sec": 180.0,
            "metadata": {"item_quality": "common", "damage": 5},
        },
    ]
    for o in objects:
        repo.save(o)


# ── server bootstrap ───────────────────────────────────────────────

def _build_server() -> dict:
    """
    Construct every server component and start zone controllers.

    Returns a dict of named references for the terminal loop.
    """
    db = Database(":memory:")
    db.connect()

    zone_repo = ZoneRepository(db)
    mob_repo = MobTemplateRepository(db)
    player_repo = PlayerRepository(db)
    map_obj_repo = MapObjectRepository(db)

    _seed_zones(zone_repo)
    _seed_mobs(mob_repo)
    _seed_map_objects(map_obj_repo)

    event_bus = EventBus()
    world = World()
    connections = ConnectionManager()

    movement = MovementSystem(world, event_bus)
    combat = CombatSystem(world, event_bus, base_damage=15)
    sync = SyncSystem(world, event_bus, connections)
    interaction = InteractionSystem(world)

    controllers: dict[str, ZoneController] = {}

    for row in zone_repo.list_all():
        zone = Zone(
            zone_id=row["id"],
            name=row["name"],
            bounds=ZoneBounds(row["min_x"], row["min_y"],
                              row["max_x"], row["max_y"]),
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

        for t in map_obj_repo.load_by_zone(zone.zone_id):
            obj = MapObjectFactory.from_template(t)
            controller.register_map_object(obj)

        controllers[zone.zone_id] = controller

    return {
        "db": db,
        "player_repo": player_repo,
        "world": world,
        "connections": connections,
        "movement": movement,
        "combat": combat,
        "interaction": interaction,
        "controllers": controllers,
        "event_bus": event_bus,
    }


# ── player helpers ─────────────────────────────────────────────────

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


def _disconnect_player(srv: dict, player_id: str) -> None:
    """Save and remove a player from the world."""
    pos = srv["world"].get_entity_position(player_id)
    entity = srv["world"].get_entity(player_id)
    if entity and pos:
        srv["player_repo"].save({
            "id": player_id, "name": entity.name,
            "race": "", "class": "", "level": entity.level,
            "health": entity.health.current, "mana": 0,
            "position_x": pos[0], "position_y": pos[1],
            "stats_json": {},
        })
    srv["world"].remove_entity(player_id)
    srv["connections"].remove(player_id)
    print(f"  [{player_id}] disconnected and saved.")


# ── terminal command loop ──────────────────────────────────────────

def _print_help() -> None:
    print("""
Commands:
  connect <id> <n> <race> <class> <x> <y>  — join the world
  disconnect <id>                              — leave and save
  move <id> <x> <y>                            — move a player
  attack <id> <target>                         — attack a target
  interact <player_id> <object_id>             — interact with map object
  status <id>                                  — entity info
  nearby <id>                                  — nearby entities
  mobs                                         — all live mobs
  objects                                      — all map objects
  zones                                        — zone info
  watch [seconds]                              — watch the world live
  quit                                         — shut down

Races:   Human, Dwarf, Night Elf, Gnome, Orc, Tauren, Troll, Undead
Classes: Hunter, Mage, Druid, Paladin, Priest, Rogue, Shaman, Warlock, Warrior
""")


def _watch_world(srv: dict, duration: float) -> None:
    """Print a live snapshot of the world every half-second."""
    end = time.monotonic() + duration
    while time.monotonic() < end:
        print(f"\n--- World snapshot (t={time.monotonic():.1f}) ---")
        for zid, ctrl in srv["controllers"].items():
            print(f"  Zone '{zid}': ticks={ctrl.tick_count}, "
                  f"mobs={ctrl.mob_count}, objects={ctrl.map_objects.count}")

        for zid, ctrl in srv["controllers"].items():
            for mid, mob in list(ctrl._mobs.items()):
                pos = srv["world"].get_entity_position(mid)
                state = mob.brain.state.value
                target = mob.brain.target_id or "-"
                hp = f"{mob.entity.health.current}/{mob.entity.health.maximum}"
                pos_str = f"({pos[0]:.1f}, {pos[1]:.1f})" if pos else "(?)"
                print(f"    {mob.display_name:16s} {pos_str:16s} "
                      f"hp={hp:8s} state={state:16s} target={target}")

        player_ids = srv["connections"].get_all_ids()
        for pid in sorted(player_ids):
            e = srv["world"].get_entity(pid)
            p = srv["world"].get_entity_position(pid)
            zone = srv["world"].get_entity_zone_id(pid) or "OUTSIDE"
            if e and p:
                hp = f"{e.health.current}/{e.health.maximum}"
                print(f"    Player {pid:12s} ({p[0]:.1f}, {p[1]:.1f}) "
                      f"hp={hp:8s} zone={zone}")
        time.sleep(0.5)


def run() -> None:
    """Boot the server with live zone controllers."""
    print("=" * 55)
    print("  GAME SERVER — live zone controllers")
    print("=" * 55)

    srv = _build_server()

    for zid, ctrl in srv["controllers"].items():
        ctrl.start()
        print(f"  Zone '{zid}' controller started "
              f"({ctrl.mob_count} mobs, {ctrl.map_objects.count} map objects)")

    print("\nWorld is LIVE. Mobs are patrolling.")
    print("Type 'help' for commands.\n")

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

        elif cmd == "disconnect" and len(parts) >= 2:
            _disconnect_player(srv, parts[1])

        elif cmd == "move" and len(parts) >= 4:
            srv["movement"].enqueue(
                MoveIntent(parts[1], float(parts[2]), float(parts[3]))
            )

        elif cmd == "attack" and len(parts) >= 3:
            srv["combat"].enqueue(AttackIntent(parts[1], parts[2]))

        elif cmd == "interact" and len(parts) >= 3:
            player_id = parts[1]
            object_id = parts[2]
            zone_id = srv["world"].get_entity_zone_id(player_id)
            if not zone_id:
                print(f"  Player '{player_id}' is not in a zone.")
                continue
            ctrl = srv["controllers"].get(zone_id)
            if not ctrl:
                print(f"  No controller for zone '{zone_id}'.")
                continue
            result = srv["interaction"].interact(
                player_id, object_id, ctrl.map_objects
            )
            if result.success:
                obj = result.object_data
                print(f"  [{player_id}] {obj['interaction_type']}d '{obj['name']}' "
                      f"at ({obj['position']['x']:.0f}, {obj['position']['y']:.0f})")
            else:
                print(f"  Failed: {result.reason}")

        elif cmd == "status" and len(parts) >= 2:
            eid = parts[1]
            entity = srv["world"].get_entity(eid)
            pos = srv["world"].get_entity_position(eid)
            zone_id = srv["world"].get_entity_zone_id(eid)
            if entity:
                print(f"  {entity}")
                print(f"  Position: {pos}")
                print(f"  Zone: {zone_id or 'OUTSIDE'}")
                print(f"  HP: {entity.health.current}/{entity.health.maximum}")
                print(f"  Alive: {entity.is_alive}")
            else:
                print(f"  Entity '{eid}' not found (dead or despawned).")

        elif cmd == "nearby" and len(parts) >= 2:
            ids = srv["world"].get_nearby_entity_ids(parts[1])
            if ids:
                for nid in sorted(ids):
                    e = srv["world"].get_entity(nid)
                    p = srv["world"].get_entity_position(nid)
                    hp = e.health.current if e else "?"
                    print(f"  {nid}: pos={p}  hp={hp}")
            else:
                print("  No nearby entities (outside zone or alone).")

        elif cmd == "mobs":
            for zid, ctrl in srv["controllers"].items():
                print(f"  Zone '{zid}' (ticks={ctrl.tick_count}):")
                for mid, mob in list(ctrl._mobs.items()):
                    pos = srv["world"].get_entity_position(mid)
                    state = mob.brain.state.value
                    target = mob.brain.target_id or "-"
                    hp = f"{mob.entity.health.current}/{mob.entity.health.maximum}"
                    pos_str = f"({pos[0]:.1f}, {pos[1]:.1f})" if pos else "(?)"
                    print(f"    {mob.display_name:16s} {pos_str:16s} "
                          f"hp={hp:8s} state={state:16s} target={target}")
                if not ctrl._mobs:
                    print("    (all mobs dead, awaiting respawn)")

        elif cmd == "objects":
            for zid, ctrl in srv["controllers"].items():
                print(f"  Zone '{zid}':")
                for obj in ctrl.map_objects.get_all():
                    state = "active" if obj.active else "inactive"
                    pos = obj.position
                    print(f"    {obj.name:20s} ({pos.x:.0f}, {pos.y:.0f}) "
                          f"{obj.object_type.value:15s} {obj.interaction_type.value:10s} "
                          f"[{state}]")
                if ctrl.map_objects.count == 0:
                    print("    (no map objects)")

        elif cmd == "zones":
            for zid, ctrl in srv["controllers"].items():
                z = ctrl.zone
                b = z.bounds
                print(f"  {zid}: '{z.name}' "
                      f"[{b.min_x},{b.min_y} -> {b.max_x},{b.max_y}] "
                      f"ticks={ctrl.tick_count} mobs={ctrl.mob_count} "
                      f"objects={ctrl.map_objects.count} "
                      f"{'LIVE' if ctrl.is_running else 'STOPPED'}")

        elif cmd == "watch":
            duration = float(parts[1]) if len(parts) >= 2 else 5.0
            _watch_world(srv, duration)

        elif cmd == "quit":
            break

        else:
            print("  Unknown command. Type 'help'.")

    print("\nStopping zone controllers...")
    for ctrl in srv["controllers"].values():
        ctrl.stop()

    srv["db"].close()
    print("Server shut down.")


if __name__ == "__main__":
    run()