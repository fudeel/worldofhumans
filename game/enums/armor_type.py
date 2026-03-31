# game/enums/armor_type.py
"""Wearable armor categories."""

from enum import Enum


class ArmorType(Enum):
    """
    Armor weight classes a character can equip.

    Heavier armor generally provides more physical damage reduction.
    Classes are restricted to specific subsets of these types.
    """

    CLOTH = "Cloth"
    LEATHER = "Leather"
    MAIL = "Mail"
    PLATE = "Plate"
    SHIELD = "Shield"