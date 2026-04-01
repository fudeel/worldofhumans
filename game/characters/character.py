# game/characters/character.py
"""
Fully-featured game character built on top of ``LivingEntity``.

A ``Character`` adds class identity, race, a stat block,
secondary resource pools, an inventory, a currency balance,
and a quest log to the base living-entity contract.
It is the shared foundation for both player-controlled heroes
and server-controlled NPCs.
"""

from __future__ import annotations

from game.characters.living_entity import LivingEntity
from game.components.class_definition import ClassDefinition
from game.components.currency import Currency
from game.components.inventory import Inventory
from game.components.quest_log import QuestLog
from game.components.resource_pool import ResourcePool
from game.components.stat_block import StatBlock
from game.enums.faction import Faction
from game.enums.race import Race
from game.enums.resource_type import ResourceType


class Character(LivingEntity):
    """
    A living entity with a class, race, stats, and resource pools.

    Validates that the chosen race is legal for the given class
    definition at creation time.

    Parameters
    ----------
    name:
        Display name of the character.
    race:
        Chosen race (must be in the class definition's allowed set).
    class_def:
        The ``ClassDefinition`` blueprint this character follows.
    level:
        Starting level.
    base_health:
        Maximum health at the given level.
    base_stats:
        Optional starting stat values.
    inventory_capacity:
        Number of bag slots the character starts with.
    starting_copper:
        Initial copper balance (default 0).
    """

    def __init__(
        self,
        name: str,
        race: Race,
        class_def: ClassDefinition,
        level: int = 1,
        base_health: int = 100,
        base_stats: dict | None = None,
        inventory_capacity: int = 8,
        starting_copper: int = 0,
    ) -> None:
        if not class_def.supports_race(race):
            raise ValueError(
                f"{race.value} cannot be a {class_def.class_type.value}."
            )

        super().__init__(name=name, max_health=base_health, level=level)

        self._race = race
        self._class_def = class_def
        self._stats = StatBlock(base_stats)
        self._resources: dict[ResourceType, ResourcePool] = (
            self._build_resource_pools()
        )
        self._inventory = Inventory(capacity=inventory_capacity)
        self._currency = Currency(copper=starting_copper)
        self._quest_log = QuestLog()

    # -- identity ------------------------------------------------------------

    @property
    def race(self) -> Race:
        """The character's race."""
        return self._race

    @property
    def faction(self) -> Faction:
        """Derived from the character's race."""
        return self._race.faction

    @property
    def class_definition(self) -> ClassDefinition:
        """The class blueprint this character was created from."""
        return self._class_def

    @property
    def class_name(self) -> str:
        """Human-readable class name."""
        return self._class_def.class_type.value

    # -- stats ---------------------------------------------------------------

    @property
    def stats(self) -> StatBlock:
        """Mutable stat block for this character."""
        return self._stats

    # -- resources -----------------------------------------------------------

    @property
    def resources(self) -> dict[ResourceType, ResourcePool]:
        """All secondary resource pools (excludes Health)."""
        return self._resources

    def get_resource(self, rtype: ResourceType) -> ResourcePool | None:
        """Return a specific resource pool, or ``None`` if absent."""
        return self._resources.get(rtype)

    # -- inventory -----------------------------------------------------------

    @property
    def inventory(self) -> Inventory:
        """The character's bag / inventory container."""
        return self._inventory

    # -- currency ------------------------------------------------------------

    @property
    def currency(self) -> Currency:
        """The character's money balance."""
        return self._currency

    # -- quest log -----------------------------------------------------------

    @property
    def quest_log(self) -> QuestLog:
        """The character's quest journal."""
        return self._quest_log

    # -- internal helpers ----------------------------------------------------

    def _build_resource_pools(self) -> dict[ResourceType, ResourcePool]:
        """
        Create secondary resource pools dictated by the class definition.

        Health is handled by the parent ``LivingEntity`` and is
        intentionally excluded here.
        """
        pools: dict[ResourceType, ResourcePool] = {}
        defaults = {
            ResourceType.MANA: 200,
            ResourceType.RAGE: 100,
            ResourceType.ENERGY: 100,
        }
        for rtype in self._class_def.resource_types:
            if rtype is ResourceType.HEALTH:
                continue
            pools[rtype] = ResourcePool(rtype, defaults.get(rtype, 100))
        return pools

    # -- dunder --------------------------------------------------------------

    def __repr__(self) -> str:
        status = "alive" if self.is_alive else "dead"
        return (
            f"Character('{self.name}', {self._race.value} "
            f"{self.class_name}, lv{self.level}, {status})"
        )