# game/definitions/druid.py
"""Druid class definition — versatile hybrid with shapeshifting forms."""

from game.components.class_definition import ClassDefinition
from game.enums.armor_type import ArmorType
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType
from game.enums.role import Role
from game.enums.stat_type import StatType
from game.enums.weapon_type import WeaponType

DRUID = ClassDefinition(
    class_type=CharacterClassType.DRUID,
    description=(
        "Hybrid class that shifts between caster, bear, and cat forms to "
        "fill damage, tank, or healer roles with strong group utility."
    ),
    allowed_races=frozenset({Race.NIGHT_ELF, Race.TAUREN}),
    roles=frozenset({Role.TANK, Role.HEALER, Role.MELEE_DPS, Role.RANGED_DPS}),
    resource_types=frozenset({
        ResourceType.HEALTH, ResourceType.MANA,
        ResourceType.RAGE, ResourceType.ENERGY,
    }),
    armor_types=frozenset({ArmorType.CLOTH, ArmorType.LEATHER}),
    weapon_types=frozenset({
        WeaponType.STAFF, WeaponType.MACE_1H, WeaponType.MACE_2H,
        WeaponType.DAGGER, WeaponType.FIST_WEAPON,
    }),
    primary_stats=frozenset({
        StatType.INTELLECT, StatType.SPIRIT, StatType.CRIT,
        StatType.AGILITY, StatType.HIT, StatType.STRENGTH,
        StatType.STAMINA, StatType.SPELL_POWER, StatType.HEALING_POWER,
    }),
    talent_trees=("Balance", "Feral Combat", "Restoration"),
)