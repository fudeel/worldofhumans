# game/definitions/__init__.py
"""
Class definition registry.

Import any single definition by name, or use ``CLASS_REGISTRY`` to
look up a ``ClassDefinition`` by its ``CharacterClassType`` enum.
"""

from game.components.class_definition import ClassDefinition
from game.definitions.druid import DRUID
from game.definitions.hunter import HUNTER
from game.definitions.mage import MAGE
from game.definitions.paladin import PALADIN
from game.definitions.priest import PRIEST
from game.definitions.rogue import ROGUE
from game.definitions.shaman import SHAMAN
from game.definitions.warlock import WARLOCK
from game.definitions.warrior import WARRIOR
from game.enums.character_class_type import CharacterClassType

CLASS_REGISTRY: dict[CharacterClassType, ClassDefinition] = {
    CharacterClassType.DRUID: DRUID,
    CharacterClassType.HUNTER: HUNTER,
    CharacterClassType.MAGE: MAGE,
    CharacterClassType.PALADIN: PALADIN,
    CharacterClassType.PRIEST: PRIEST,
    CharacterClassType.ROGUE: ROGUE,
    CharacterClassType.SHAMAN: SHAMAN,
    CharacterClassType.WARLOCK: WARLOCK,
    CharacterClassType.WARRIOR: WARRIOR,
}


def get_class_definition(class_type: CharacterClassType) -> ClassDefinition:
    """
    Retrieve the ``ClassDefinition`` for *class_type*.

    Raises ``KeyError`` if the class type is not registered.
    """
    return CLASS_REGISTRY[class_type]


__all__ = [
    "CLASS_REGISTRY",
    "DRUID",
    "HUNTER",
    "MAGE",
    "PALADIN",
    "PRIEST",
    "ROGUE",
    "SHAMAN",
    "WARLOCK",
    "WARRIOR",
    "get_class_definition",
]