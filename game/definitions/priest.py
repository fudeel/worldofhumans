# game/definitions/priest.py
"""Priest class definition — primary healer with a shadow damage spec."""

from game.components.class_definition import ClassDefinition
from game.enums.armor_type import ArmorType
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType
from game.enums.role import Role
from game.enums.stat_type import StatType
from game.enums.weapon_type import WeaponType

PRIEST = ClassDefinition(
    class_type=CharacterClassType.PRIEST,
    description=(
        "Primary healer valued for powerful buffs, debuffs, and "
        "versatile healing toolkit. Shadow spec enables ranged DPS."
    ),
    allowed_races=frozenset({
        Race.HUMAN, Race.DWARF, Race.NIGHT_ELF,
        Race.UNDEAD, Race.TROLL,
    }),
    roles=frozenset({Role.HEALER, Role.RANGED_DPS}),
    resource_types=frozenset({ResourceType.HEALTH, ResourceType.MANA}),
    armor_types=frozenset({ArmorType.CLOTH}),
    weapon_types=frozenset({
        WeaponType.MACE_1H, WeaponType.DAGGER,
        WeaponType.STAFF, WeaponType.WAND, WeaponType.OFF_HAND,
    }),
    primary_stats=frozenset({
        StatType.INTELLECT, StatType.SPIRIT, StatType.HIT,
        StatType.CRIT, StatType.MP5,
        StatType.SPELL_POWER, StatType.HEALING_POWER,
    }),
    talent_trees=("Discipline", "Holy", "Shadow"),
)