# game/components/mob_brain.py
"""
Per-mob AI state machine.

Each tick the brain evaluates the mob's surroundings and
decides on the next state and action.  The zone controller
reads the brain's output and enqueues the corresponding
movement or attack intents.
"""

from __future__ import annotations

import random

from game.components.vector2 import Vector2
from game.enums.aggression_type import AggressionType
from game.enums.mob_state import MobState


class MobBrain:
    """
    Decides what a single mob does every tick.

    Parameters
    ----------
    aggression:
        Whether the mob attacks unprovoked.
    aggro_range:
        Detection radius for aggressive targeting.
    attack_range:
        Maximum distance to deal damage.
    leash_range:
        Maximum distance from spawn before the mob resets.
    patrol_radius:
        Wander distance from spawn during IDLE/PATROL.
    move_speed:
        World units the mob can travel per second.
    attack_cooldown:
        Minimum seconds between attacks.
    """

    def __init__(
        self,
        aggression: AggressionType,
        aggro_range: float = 80.0,
        attack_range: float = 5.0,
        leash_range: float = 200.0,
        patrol_radius: float = 30.0,
        move_speed: float = 40.0,
        attack_cooldown: float = 2.0,
    ) -> None:
        self._aggression = aggression
        self._aggro_range = aggro_range
        self._attack_range = attack_range
        self._leash_range = leash_range
        self._patrol_radius = patrol_radius
        self._move_speed = move_speed
        self._attack_cooldown = attack_cooldown

        self._state = MobState.IDLE
        self._target_id: str | None = None
        self._patrol_dest: Vector2 | None = None
        self._idle_timer: float = 0.0
        self._attack_timer: float = 0.0

    # -- read-only properties ------------------------------------------------

    @property
    def state(self) -> MobState:
        """Current AI state."""
        return self._state

    @property
    def target_id(self) -> str | None:
        """Entity id the mob is currently focused on."""
        return self._target_id

    @property
    def aggression(self) -> AggressionType:
        return self._aggression

    @property
    def attack_range(self) -> float:
        return self._attack_range

    @property
    def move_speed(self) -> float:
        return self._move_speed

    # -- external triggers ---------------------------------------------------

    def on_provoked(self, attacker_id: str) -> None:
        """
        Called when a player attacks this mob.

        Forces the mob into CHASE regardless of aggression type.
        """
        if self._state in (MobState.DEAD,):
            return
        self._target_id = attacker_id
        self._state = MobState.CHASE

    def on_died(self) -> None:
        """Transition to DEAD state."""
        self._state = MobState.DEAD
        self._target_id = None
        self._patrol_dest = None

    def on_respawned(self) -> None:
        """Reset to IDLE after respawn."""
        self._state = MobState.IDLE
        self._target_id = None
        self._patrol_dest = None
        self._idle_timer = 0.0
        self._attack_timer = 0.0

    # -- per-tick evaluation -------------------------------------------------

    def evaluate(
        self,
        mob_pos: Vector2,
        spawn_pos: Vector2,
        nearby_player_ids: list[str],
        player_positions: dict[str, Vector2],
        dt: float,
    ) -> dict:
        """
        Run one AI tick and return the action to perform.

        Returns a dict with keys:

        - ``"action"``: one of ``"move"``, ``"attack"``, ``"idle"``
        - ``"target_id"``: entity to attack (if action is attack)
        - ``"move_to"``: ``Vector2`` destination (if action is move)
        """
        self._attack_timer = max(0.0, self._attack_timer - dt)

        if self._state == MobState.DEAD:
            return {"action": "idle"}

        if self._state == MobState.RETURN_TO_SPAWN:
            return self._do_return(mob_pos, spawn_pos, dt)

        if self._is_leashed(mob_pos, spawn_pos):
            return self._start_return(mob_pos, spawn_pos, dt)

        if self._state in (MobState.CHASE, MobState.ATTACK):
            return self._do_combat(mob_pos, spawn_pos, player_positions, dt)

        threat = self._scan_for_threat(mob_pos, nearby_player_ids, player_positions)
        if threat:
            self._target_id = threat
            self._state = MobState.CHASE
            return self._do_combat(mob_pos, spawn_pos, player_positions, dt)

        return self._do_patrol(mob_pos, spawn_pos, dt)

    # -- state handlers ------------------------------------------------------

    def _do_combat(
        self,
        mob_pos: Vector2,
        spawn_pos: Vector2,
        player_positions: dict[str, Vector2],
        dt: float,
    ) -> dict:
        """Handle CHASE and ATTACK states."""
        if self._target_id is None or self._target_id not in player_positions:
            self._target_id = None
            self._state = MobState.RETURN_TO_SPAWN
            return self._do_return(mob_pos, spawn_pos, dt)

        target_pos = player_positions[self._target_id]
        dist = mob_pos.distance_to(target_pos)

        if dist <= self._attack_range:
            self._state = MobState.ATTACK
            if self._attack_timer <= 0.0:
                self._attack_timer = self._attack_cooldown
                return {"action": "attack", "target_id": self._target_id}
            return {"action": "idle"}

        self._state = MobState.CHASE
        dest = mob_pos.move_toward(target_pos, self._move_speed * dt)
        return {"action": "move", "move_to": dest}

    def _do_patrol(
        self, mob_pos: Vector2, spawn_pos: Vector2, dt: float
    ) -> dict:
        """Handle IDLE and PATROL states."""
        if self._state == MobState.IDLE:
            self._idle_timer -= dt
            if self._idle_timer > 0:
                return {"action": "idle"}
            self._pick_patrol_dest(spawn_pos)
            self._state = MobState.PATROL

        if self._patrol_dest is None:
            self._state = MobState.IDLE
            self._idle_timer = random.uniform(2.0, 5.0)
            return {"action": "idle"}

        dist = mob_pos.distance_to(self._patrol_dest)
        if dist < 2.0:
            self._patrol_dest = None
            self._state = MobState.IDLE
            self._idle_timer = random.uniform(2.0, 5.0)
            return {"action": "idle"}

        patrol_speed = self._move_speed * 0.4
        dest = mob_pos.move_toward(self._patrol_dest, patrol_speed * dt)
        return {"action": "move", "move_to": dest}

    def _start_return(
        self, mob_pos: Vector2, spawn_pos: Vector2, dt: float
    ) -> dict:
        """Trigger the return-to-spawn sequence and drop aggro."""
        self._state = MobState.RETURN_TO_SPAWN
        self._target_id = None
        return self._do_return(mob_pos, spawn_pos, dt)

    def _do_return(
        self, mob_pos: Vector2, spawn_pos: Vector2, dt: float
    ) -> dict:
        """Walk back to spawn and reset."""
        dist = mob_pos.distance_to(spawn_pos)
        if dist < 2.0:
            self._state = MobState.IDLE
            self._target_id = None
            self._idle_timer = 1.0
            return {"action": "idle"}

        return_speed = self._move_speed * 1.5
        dest = mob_pos.move_toward(spawn_pos, return_speed * dt)
        return {"action": "move", "move_to": dest}

    # -- helpers -------------------------------------------------------------

    def _scan_for_threat(
        self,
        mob_pos: Vector2,
        nearby_player_ids: list[str],
        player_positions: dict[str, Vector2],
    ) -> str | None:
        """Return the closest player within aggro range, or ``None``."""
        if self._aggression != AggressionType.AGGRESSIVE:
            return None

        closest_id: str | None = None
        closest_dist = self._aggro_range

        for pid in nearby_player_ids:
            ppos = player_positions.get(pid)
            if ppos is None:
                continue
            dist = mob_pos.distance_to(ppos)
            if dist < closest_dist:
                closest_dist = dist
                closest_id = pid

        return closest_id

    def _is_leashed(self, mob_pos: Vector2, spawn_pos: Vector2) -> bool:
        """Check if the mob has been pulled beyond its leash."""
        return mob_pos.distance_to(spawn_pos) > self._leash_range

    def _pick_patrol_dest(self, spawn_pos: Vector2) -> None:
        """Choose a random patrol destination within radius of spawn."""
        angle = random.uniform(0, 2 * 3.14159)
        dist = random.uniform(5.0, self._patrol_radius)
        import math
        self._patrol_dest = Vector2(
            spawn_pos.x + math.cos(angle) * dist,
            spawn_pos.y + math.sin(angle) * dist,
        )