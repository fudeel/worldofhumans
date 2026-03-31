# game/enums/weapon_type.py
"""Weapon categories equippable by characters."""

from enum import Enum


class WeaponType(Enum):
    """
    All weapon types available in the game.

    One-handed (1H) and two-handed (2H) variants are separate entries
    because class restrictions often differ between them.
    """

    SWORD_1H = "Sword (1H)"
    SWORD_2H = "Sword (2H)"
    AXE_1H = "Axe (1H)"
    AXE_2H = "Axe (2H)"
    MACE_1H = "Mace (1H)"
    MACE_2H = "Mace (2H)"
    DAGGER = "Dagger"
    FIST_WEAPON = "Fist Weapon"
    STAFF = "Staff"
    POLEARM = "Polearm"
    BOW = "Bow"
    CROSSBOW = "Crossbow"
    GUN = "Gun"
    WAND = "Wand"
    THROWN = "Thrown"
    OFF_HAND = "Off-Hand"