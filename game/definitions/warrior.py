# game/definitions/warrior.py
"""Warrior class definition — main tank and melee DPS available to all races."""

from game.components.class_definition import ClassDefinition
from game.enums.armor_type import ArmorType
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType
from game.enums.role import Role
from game.enums.stat_type import StatType
from game.enums.weapon_type import WeaponType

WARRIOR = ClassDefinition(
    class_type=CharacterClassType.WARRIOR,
    description=(
        "Premier main tank and strong melee DPS available to every race. "
        "Excels at end-game scaling but suffers from slow solo levelling "
        "and long cooldowns."
    ),
    allowed_races=frozenset({
        Race.HUMAN, Race.DWARF, Race.NIGHT_ELF, Race.GNOME,
        Race.ORC, Race.TAUREN, Race.TROLL, Race.UNDEAD,
    }),
    roles=frozenset({Role.TANK, Role.MELEE_DPS}),
    resource_types=frozenset({ResourceType.HEALTH, ResourceType.RAGE}),
    armor_types=frozenset({
        ArmorType.CLOTH, ArmorType.LEATHER,
        ArmorType.MAIL, ArmorType.PLATE, ArmorType.SHIELD,
    }),
    weapon_types=frozenset({
        WeaponType.SWORD_1H, WeaponType.SWORD_2H,
        WeaponType.AXE_1H, WeaponType.AXE_2H,
        WeaponType.MACE_1H, WeaponType.MACE_2H,
        WeaponType.DAGGER, WeaponType.FIST_WEAPON,
        WeaponType.STAFF, WeaponType.POLEARM,
        WeaponType.BOW, WeaponType.CROSSBOW, WeaponType.GUN,
        WeaponType.THROWN,
    }),
    primary_stats=frozenset({
        StatType.STRENGTH, StatType.STAMINA,
        StatType.HIT, StatType.CRIT,
        StatType.ARMOR, StatType.DEFENSE, StatType.AGILITY,
    }),
    talent_trees=("Arms", "Fury", "Protection"),
)