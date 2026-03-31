# game/definitions/rogue.py
"""Rogue class definition — stealthy melee dealer with lockpicking."""

from game.components.class_definition import ClassDefinition
from game.enums.armor_type import ArmorType
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType
from game.enums.role import Role
from game.enums.stat_type import StatType
from game.enums.weapon_type import WeaponType

ROGUE = ClassDefinition(
    class_type=CharacterClassType.ROGUE,
    description=(
        "Melee damage dealer specialising in sustained single-target "
        "damage, stealth, opponent lockdown, and opening locked objects."
    ),
    allowed_races=frozenset({
        Race.GNOME, Race.HUMAN, Race.DWARF, Race.NIGHT_ELF,
        Race.ORC, Race.UNDEAD, Race.TROLL,
    }),
    roles=frozenset({Role.MELEE_DPS}),
    resource_types=frozenset({ResourceType.HEALTH, ResourceType.ENERGY}),
    armor_types=frozenset({ArmorType.CLOTH, ArmorType.LEATHER}),
    weapon_types=frozenset({
        WeaponType.DAGGER, WeaponType.SWORD_1H, WeaponType.MACE_1H,
        WeaponType.FIST_WEAPON, WeaponType.THROWN,
        WeaponType.GUN, WeaponType.BOW, WeaponType.CROSSBOW,
    }),
    primary_stats=frozenset({
        StatType.AGILITY, StatType.STRENGTH,
        StatType.HIT, StatType.CRIT,
    }),
    talent_trees=("Assassination", "Combat", "Subtlety"),
)