# game/definitions/paladin.py
"""Paladin class definition — Alliance-only hybrid with blessings and auras."""

from game.components.class_definition import ClassDefinition
from game.enums.armor_type import ArmorType
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType
from game.enums.role import Role
from game.enums.stat_type import StatType
from game.enums.weapon_type import WeaponType

PALADIN = ClassDefinition(
    class_type=CharacterClassType.PALADIN,
    description=(
        "Alliance-only hybrid support class providing competitive healing, "
        "dungeon tanking, and unique blessings and auras for the group."
    ),
    allowed_races=frozenset({Race.DWARF, Race.HUMAN}),
    roles=frozenset({Role.TANK, Role.HEALER, Role.MELEE_DPS}),
    resource_types=frozenset({ResourceType.HEALTH, ResourceType.MANA}),
    armor_types=frozenset({
        ArmorType.CLOTH, ArmorType.LEATHER,
        ArmorType.MAIL, ArmorType.PLATE, ArmorType.SHIELD,
    }),
    weapon_types=frozenset({
        WeaponType.AXE_1H, WeaponType.AXE_2H,
        WeaponType.MACE_1H, WeaponType.MACE_2H,
        WeaponType.SWORD_1H, WeaponType.SWORD_2H,
        WeaponType.POLEARM, WeaponType.OFF_HAND,
    }),
    primary_stats=frozenset({
        StatType.STAMINA, StatType.SPIRIT, StatType.MP5,
        StatType.INTELLECT, StatType.CRIT, StatType.HEALING_POWER,
        StatType.STRENGTH, StatType.DEFENSE, StatType.HIT,
        StatType.ARMOR, StatType.AGILITY,
    }),
    talent_trees=("Holy", "Retribution", "Protection"),
)