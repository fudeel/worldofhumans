# game/components/class_definition.py
"""
Immutable blueprint describing a playable character class.

A ``ClassDefinition`` holds the static data that is shared by every
character of that class: allowed races, equippable gear, talent tree
names, available roles, and resource types.  It carries no mutable
state and is safe to reference from many characters simultaneously.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game.enums.armor_type import ArmorType
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType
from game.enums.role import Role
from game.enums.stat_type import StatType
from game.enums.weapon_type import WeaponType


@dataclass(frozen=True)
class ClassDefinition:
    """
    Static template for a character class.

    Parameters
    ----------
    class_type:
        Enum identifier for the class (e.g. ``CharacterClassType.HUNTER``).
    description:
        Short flavour text shown in character creation.
    allowed_races:
        Races that may pick this class.
    roles:
        Combat roles the class can fulfil.
    resource_types:
        Resource pools the class uses (Health is always implied).
    armor_types:
        Armor categories the class may equip.
    weapon_types:
        Weapon categories the class may equip.
    primary_stats:
        Stats most important for the class across all specs.
    talent_trees:
        Ordered tuple of three talent-tree names.
    """

    class_type: CharacterClassType
    description: str
    allowed_races: frozenset[Race]
    roles: frozenset[Role]
    resource_types: frozenset[ResourceType]
    armor_types: frozenset[ArmorType]
    weapon_types: frozenset[WeaponType]
    primary_stats: frozenset[StatType]
    talent_trees: tuple[str, str, str]

    # -- queries -------------------------------------------------------------

    def supports_race(self, race: Race) -> bool:
        """Return ``True`` if *race* can be this class."""
        return race in self.allowed_races

    def can_equip_armor(self, armor: ArmorType) -> bool:
        """Return ``True`` if this class may wear *armor*."""
        return armor in self.armor_types

    def can_equip_weapon(self, weapon: WeaponType) -> bool:
        """Return ``True`` if this class may wield *weapon*."""
        return weapon in self.weapon_types

    def has_role(self, role: Role) -> bool:
        """Return ``True`` if this class can perform *role*."""
        return role in self.roles

    def uses_resource(self, resource: ResourceType) -> bool:
        """Return ``True`` if this class relies on *resource*."""
        return resource in self.resource_types

    def __str__(self) -> str:
        return f"{self.class_type.value} — {self.description}"