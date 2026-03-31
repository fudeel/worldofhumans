# game/enums/race.py
"""Playable races and their faction affiliation."""

from enum import Enum

from game.enums.faction import Faction


class Race(Enum):
    """
    Playable races in Classic WoW.

    Each race belongs to exactly one faction, accessible via the
    ``faction`` property.
    """

    HUMAN = "Human"
    DWARF = "Dwarf"
    NIGHT_ELF = "Night Elf"
    GNOME = "Gnome"
    ORC = "Orc"
    TAUREN = "Tauren"
    TROLL = "Troll"
    UNDEAD = "Undead"

    @property
    def faction(self) -> Faction:
        """Return the faction this race belongs to."""
        return _RACE_FACTION_MAP[self]


_RACE_FACTION_MAP: dict[Race, Faction] = {
    Race.HUMAN: Faction.ALLIANCE,
    Race.DWARF: Faction.ALLIANCE,
    Race.NIGHT_ELF: Faction.ALLIANCE,
    Race.GNOME: Faction.ALLIANCE,
    Race.ORC: Faction.HORDE,
    Race.TAUREN: Faction.HORDE,
    Race.TROLL: Faction.HORDE,
    Race.UNDEAD: Faction.HORDE,
}