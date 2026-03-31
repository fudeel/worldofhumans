# game/characters/__init__.py
"""Character hierarchy: LivingEntity → Character."""

from game.characters.character import Character
from game.characters.living_entity import LivingEntity

__all__ = [
    "Character",
    "LivingEntity",
]