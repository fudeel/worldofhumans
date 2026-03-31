# game/world/mob_instance.py
"""
Runtime mob entity combining a ``LivingEntity`` with AI and spawn data.

``MobInstance`` is the object the zone controller works with
each tick.  It wraps everything needed to drive one mob:
the living entity (health), the brain (decisions), and the
spawn configuration (where it came from, how to respawn).
"""

from __future__ import annotations

from game.characters.living_entity import LivingEntity
from game.components.mob_brain import MobBrain
from game.components.vector2 import Vector2
from game.enums.aggression_type import AggressionType
from game.enums.mob_state import MobState


class MobInstance:
    """
    A single live mob in the world.

    Parameters
    ----------
    template:
        The database row dict that describes this mob's blueprint.
    entity:
        The ``LivingEntity`` placed in the world.
    brain:
        The AI state machine driving behaviour.
    spawn_pos:
        The original spawn location for leash / respawn.
    """

    def __init__(
        self,
        template: dict,
        entity: LivingEntity,
        brain: MobBrain,
        spawn_pos: Vector2,
    ) -> None:
        self._template = template
        self._entity = entity
        self._brain = brain
        self._spawn_pos = spawn_pos

    # -- read-only access ----------------------------------------------------

    @property
    def mob_id(self) -> str:
        """Unique identifier (matches the template id)."""
        return self._template["id"]

    @property
    def display_name(self) -> str:
        """Human-readable name for messages."""
        return self._template["name"]

    @property
    def entity(self) -> LivingEntity:
        """The underlying living entity."""
        return self._entity

    @property
    def brain(self) -> MobBrain:
        """The AI state machine."""
        return self._brain

    @property
    def spawn_pos(self) -> Vector2:
        """Original spawn position."""
        return self._spawn_pos

    @property
    def template(self) -> dict:
        """Raw template dict from the database."""
        return self._template

    @property
    def respawn_sec(self) -> float:
        """Seconds until this mob respawns after death."""
        return float(self._template.get("respawn_sec", 60))

    @property
    def is_alive(self) -> bool:
        """``True`` while the entity has health remaining."""
        return self._entity.is_alive

    @property
    def state(self) -> MobState:
        """Current AI state (delegates to brain)."""
        return self._brain.state

    # -- factory -------------------------------------------------------------

    @classmethod
    def from_template(cls, template: dict) -> "MobInstance":
        """
        Construct a ``MobInstance`` from a database template row.

        Reads ``aggression_type``, ``aggro_range``, ``leash_range``,
        ``patrol_radius``, ``move_speed``, and ``attack_cooldown``
        from the template, falling back to sensible defaults.
        """
        aggression = AggressionType(
            template.get("aggression_type", AggressionType.PASSIVE.value)
        )
        brain = MobBrain(
            aggression=aggression,
            aggro_range=float(template.get("aggro_range", 80.0)),
            attack_range=float(template.get("attack_range", 5.0)),
            leash_range=float(template.get("leash_range", 200.0)),
            patrol_radius=float(template.get("patrol_radius", 30.0)),
            move_speed=float(template.get("move_speed", 40.0)),
            attack_cooldown=float(template.get("attack_cooldown", 2.0)),
        )
        entity = LivingEntity(
            name=template["id"],
            max_health=template["base_health"],
            level=template.get("level", 1),
        )
        spawn = Vector2(template["spawn_x"], template["spawn_y"])

        return cls(template=template, entity=entity,
                   brain=brain, spawn_pos=spawn)

    def __repr__(self) -> str:
        return (
            f"MobInstance('{self.mob_id}', '{self.display_name}', "
            f"state={self.state.value}, alive={self.is_alive})"
        )