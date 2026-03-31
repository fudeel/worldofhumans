# game/definitions/mage.py
"""Mage class definition — ranged caster with AoE and crowd control."""

from game.components.class_definition import ClassDefinition
from game.enums.armor_type import ArmorType
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType
from game.enums.role import Role
from game.enums.stat_type import StatType
from game.enums.weapon_type import WeaponType

MAGE = ClassDefinition(
    class_type=CharacterClassType.MAGE,
    description=(
        "Ranged damage dealer excelling at single-target burst, sustained "
        "AoE, and crowd control. Conjures food, water, and city portals."
    ),
    allowed_races=frozenset({
        Race.HUMAN, Race.GNOME,
        Race.UNDEAD, Race.TROLL,
    }),
    roles=frozenset({Role.RANGED_DPS}),
    resource_types=frozenset({ResourceType.HEALTH, ResourceType.MANA}),
    armor_types=frozenset({ArmorType.CLOTH}),
    weapon_types=frozenset({
        WeaponType.STAFF, WeaponType.WAND, WeaponType.DAGGER,
        WeaponType.SWORD_1H, WeaponType.OFF_HAND,
    }),
    primary_stats=frozenset({
        StatType.INTELLECT, StatType.HIT,
        StatType.CRIT, StatType.SPELL_POWER,
    }),
    talent_trees=("Arcane", "Fire", "Frost"),
)