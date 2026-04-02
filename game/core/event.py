# game/core/event.py
"""
Immutable event dataclasses emitted by game systems.

Every state change in the game loop produces an event that is
published to the ``EventBus``.  Subscribers (typically the sync
system) decide who needs to hear about it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EventType(Enum):
    """Discriminator for fast event filtering."""

    ENTITY_MOVED = "entity_moved"
    ENTITY_DAMAGED = "entity_damaged"
    ENTITY_DIED = "entity_died"
    ENTITY_HEALED = "entity_healed"
    ENTITY_SPAWNED = "entity_spawned"
    ENTITY_DESPAWNED = "entity_despawned"
    PLAYER_ENTERED_ZONE = "player_entered_zone"
    PLAYER_LEFT_ZONE = "player_left_zone"
    PLAYER_OUTSIDE_ZONE = "player_outside_zone"
    LOOT_DROPPED = "loot_dropped"
    LOOT_EXPIRED = "loot_expired"
    QUEST_COMPLETED = "quest_completed"
    EXPERIENCE_GAINED = "experience_gained"
    LEVEL_UP = "level_up"


@dataclass(frozen=True)
class GameEvent:
    """
    Base event carrying the type and originating entity id.

    All specialised events extend this with additional fields.
    """

    event_type: EventType
    entity_id: str


@dataclass(frozen=True)
class EntityMovedEvent(GameEvent):
    """An entity changed its world position."""

    old_x: float = 0.0
    old_y: float = 0.0
    new_x: float = 0.0
    new_y: float = 0.0


@dataclass(frozen=True)
class EntityDamagedEvent(GameEvent):
    """An entity received damage from a source."""

    source_id: str = ""
    amount: int = 0
    remaining_health: int = 0


@dataclass(frozen=True)
class EntityDiedEvent(GameEvent):
    """An entity's health reached zero."""

    killer_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0


@dataclass(frozen=True)
class EntityHealedEvent(GameEvent):
    """An entity recovered health."""

    source_id: str = ""
    amount: int = 0
    current_health: int = 0


@dataclass(frozen=True)
class EntitySpawnedEvent(GameEvent):
    """A new entity appeared in the world."""

    entity_name: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    zone_id: str = ""


@dataclass(frozen=True)
class EntityDespawnedEvent(GameEvent):
    """An entity was removed from the world."""

    position_x: float = 0.0
    position_y: float = 0.0
    zone_id: str = ""


@dataclass(frozen=True)
class PlayerEnteredZoneEvent(GameEvent):
    """A player crossed into a gaming zone boundary."""

    zone_id: str = ""
    zone_name: str = ""


@dataclass(frozen=True)
class PlayerLeftZoneEvent(GameEvent):
    """A player left a gaming zone boundary."""

    zone_id: str = ""


@dataclass(frozen=True)
class PlayerOutsideZoneEvent(GameEvent):
    """A player tried to interact but is outside all gaming zones."""

    pass


@dataclass(frozen=True)
class LootDroppedEvent(GameEvent):
    """A loot drop appeared in the world after a mob death."""

    drop_id: str = ""
    mob_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0


@dataclass(frozen=True)
class LootExpiredEvent(GameEvent):
    """A loot drop was invalidated because the mob respawned."""

    drop_id: str = ""
    mob_id: str = ""


@dataclass(frozen=True)
class QuestCompletedEvent(GameEvent):
    """A player completed all objectives of a quest."""

    quest_id: str = ""
    quest_title: str = ""


@dataclass(frozen=True)
class ExperienceGainedEvent(GameEvent):
    """A character earned experience points."""

    source: str = ""
    amount: int = 0
    current_exp: int = 0
    exp_to_next_level: int = 0
    level: int = 1


@dataclass(frozen=True)
class LevelUpEvent(GameEvent):
    """A character advanced one or more levels."""

    old_level: int = 1
    new_level: int = 1
    levels_gained: int = 1