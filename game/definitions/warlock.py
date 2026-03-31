# game/definitions/warlock.py
"""Warlock class definition — pet-wielding caster with DoTs and debuffs."""

from game.components.class_definition import ClassDefinition
from game.enums.armor_type import ArmorType
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType
from game.enums.role import Role
from game.enums.stat_type import StatType
from game.enums.weapon_type import WeaponType

WARLOCK = ClassDefinition(
    class_type=CharacterClassType.WARLOCK,
    description=(
        "Ranged caster specialising in pets, debuffs, and damage over time. "
        "Offers free mounts and valuable raid utility at the cost of "
        "health-consuming spells and Soul Shard management."
    ),
    allowed_races=frozenset({
        Race.GNOME, Race.HUMAN,
        Race.ORC, Race.UNDEAD,
    }),
    roles=frozenset({Role.RANGED_DPS}),
    resource_types=frozenset({ResourceType.HEALTH, ResourceType.MANA}),
    armor_types=frozenset({ArmorType.CLOTH}),
    weapon_types=frozenset({
        WeaponType.WAND, WeaponType.STAFF, WeaponType.DAGGER,
        WeaponType.SWORD_1H, WeaponType.OFF_HAND,
    }),
    primary_stats=frozenset({
        StatType.INTELLECT, StatType.HIT,
        StatType.CRIT, StatType.SPELL_POWER,
    }),
    talent_trees=("Affliction", "Demonology", "Destruction"),
)