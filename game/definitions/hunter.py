# game/definitions/hunter.py
"""Hunter class definition — ranged damage dealer with pet utility."""

from game.components.class_definition import ClassDefinition
from game.enums.armor_type import ArmorType
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType
from game.enums.role import Role
from game.enums.stat_type import StatType
from game.enums.weapon_type import WeaponType

HUNTER = ClassDefinition(
    class_type=CharacterClassType.HUNTER,
    description=(
        "Ranged damage dealer and designated puller who relies on pet "
        "tanks, kiting, crowd control, and combat-reset abilities."
    ),
    allowed_races=frozenset({
        Race.DWARF, Race.NIGHT_ELF,
        Race.ORC, Race.TAUREN, Race.TROLL,
    }),
    roles=frozenset({Role.RANGED_DPS}),
    resource_types=frozenset({ResourceType.HEALTH, ResourceType.MANA}),
    armor_types=frozenset({ArmorType.CLOTH, ArmorType.LEATHER, ArmorType.MAIL}),
    weapon_types=frozenset({
        WeaponType.BOW, WeaponType.CROSSBOW, WeaponType.GUN,
        WeaponType.SWORD_1H, WeaponType.SWORD_2H,
        WeaponType.AXE_1H, WeaponType.AXE_2H,
        WeaponType.FIST_WEAPON, WeaponType.POLEARM,
        WeaponType.DAGGER, WeaponType.STAFF, WeaponType.THROWN,
    }),
    primary_stats=frozenset({
        StatType.AGILITY, StatType.ATTACK_POWER,
        StatType.HIT, StatType.CRIT,
    }),
    talent_trees=("Marksmanship", "Beast Mastery", "Survival"),
)