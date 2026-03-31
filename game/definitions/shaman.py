# game/definitions/shaman.py
"""Shaman class definition — Horde-only hybrid with totems and reincarnation."""

from game.components.class_definition import ClassDefinition
from game.enums.armor_type import ArmorType
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType
from game.enums.role import Role
from game.enums.stat_type import StatType
from game.enums.weapon_type import WeaponType

SHAMAN = ClassDefinition(
    class_type=CharacterClassType.SHAMAN,
    description=(
        "Horde-only hybrid support class with powerful totem buffs, "
        "AoE healing, offensive dispels, and self-resurrection."
    ),
    allowed_races=frozenset({Race.ORC, Race.TAUREN, Race.TROLL}),
    roles=frozenset({Role.HEALER, Role.MELEE_DPS, Role.RANGED_DPS}),
    resource_types=frozenset({ResourceType.HEALTH, ResourceType.MANA}),
    armor_types=frozenset({
        ArmorType.CLOTH, ArmorType.LEATHER,
        ArmorType.MAIL, ArmorType.SHIELD,
    }),
    weapon_types=frozenset({
        WeaponType.STAFF, WeaponType.FIST_WEAPON, WeaponType.DAGGER,
        WeaponType.AXE_1H, WeaponType.AXE_2H,
        WeaponType.MACE_1H, WeaponType.MACE_2H,
        WeaponType.OFF_HAND,
    }),
    primary_stats=frozenset({
        StatType.AGILITY, StatType.HIT, StatType.CRIT,
        StatType.INTELLECT, StatType.SPIRIT, StatType.MP5,
        StatType.SPELL_POWER, StatType.HEALING_POWER,
    }),
    talent_trees=("Elemental", "Enhancement", "Restoration"),
)