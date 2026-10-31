"""
Game entities
=============

Every object that moves in the world inherits from :class:`Entity`, which
owns an axis-aligned bounding box (AABB) plus simple velocity state.

    Entity
     |-- Player            the hero (you)
     |-- Slime             patrolling enemy, can be squashed from above
     |-- Coin              a "love token" to collect
     |-- MovingPlatform    a platform that slides back and forth
     |-- Particle          confetti / dust / sparkles
     |-- Checkpoint        a flag that moves your respawn point

Inheritance keeps the shared movement, collision and geometry code in one
place, so each subclass only adds what makes it different.
"""

import math
import random

from .settings import (
    ACCEL, AIR_ACCEL, COYOTE_TIME, FRICTION, GRAVITY, INVULN_TIME,
    JUMP_BUFFER, JUMP_CUT, JUMP_VELOCITY, KNOCKBACK_X, KNOCKBACK_Y,
    MAX_FALL, MAX_HEARTS, MOVE_SPEED, PLAYER_H, PLAYER_W, SLIME_H, SLIME_W,
    START_HEARTS, TOKEN_SIZE,
)


class Entity:
    """Base class: a rectangle that can move.

    The position (``x``, ``y``) is the **top-left** corner and ``y`` grows
    downwards, which is the convention used by tkinter canvases.
    """

    def __init__(self, x, y, w, h):
        self.x = float(x)
        self.y = float(y)
        self.w = float(w)
        self.h = float(h)
        self.vx = 0.0
        self.vy = 0.0
        self.alive = True

    # -- geometry ---------------------------------------------------------
    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.w

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def center_x(self):
        return self.x + self.w / 2.0

    @property
    def center_y(self):
        return self.y + self.h / 2.0

    @property
    def rect(self):
        """Return ``(x, y, w, h)`` - the same format used by level solids."""
        return (self.x, self.y, self.w, self.h)

    def overlaps(self, rect):
        """True when this entity intersects ``rect`` = ``(x, y, w, h)``."""
        rx, ry, rw, rh = rect
        return (self.x < rx + rw and self.x + self.w > rx
                and self.y < ry + rh and self.y + self.h > ry)

    def overlaps_entity(self, other):
        return self.overlaps(other.rect)

    def update(self, dt):
        """Advance one fixed timestep.  Overridden by subclasses."""


class Player(Entity):
    """The hero.  Physics, jumping feel and damage handling live here."""

    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_W, PLAYER_H)
        self.spawn = (float(x), float(y))
        self.hearts = START_HEARTS
        self.max_hearts = MAX_HEARTS
        self.tokens = 0
        self.facing = 1            # 1 = right, -1 = left
        self.on_ground = False
        self.coyote = 0.0          # time left to still jump after a ledge
        self.jump_buffer = 0.0     # time a queued jump stays valid
        self.walk_phase = 0.0      # animation clock for the legs
        self.invuln = 0.0
        self.riding = None         # MovingPlatform currently stood on
        self.hurt_flash = 0.0

    # -- input ------------------------------------------------------------
    def request_jump(self):
        """Called on the key-press edge; the jump may fire a few frames later."""
        self.jump_buffer = JUMP_BUFFER

    def respawn(self):
        self.x, self.y = self.spawn
        self.vx = self.vy = 0.0
        self.invuln = INVULN_TIME
        self.on_ground = False

    # -- damage -----------------------------------------------------------
    def hurt(self, from_x=None):
        """Lose one heart.  Returns False when the player is out of hearts."""
        if self.invuln > 0:
            return True
        self.hearts -= 1
        self.invuln = INVULN_TIME
        self.hurt_flash = 0.35
        if from_x is not None:
            direction = -1 if self.center_x < from_x else 1
            self.vx = KNOCKBACK_X * direction
            self.vy = KNOCKBACK_Y
        return self.hearts > 0

    def heal(self):
        if self.hearts < self.max_hearts:
            self.hearts += 1

    # -- physics ----------------------------------------------------------
    def update(self, dt, solids, move_left, move_right, jump_held):
        """Integrate movement, then resolve collisions one axis at a time."""
        self.invuln = max(0.0, self.invuln - dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt)

        # ---- horizontal acceleration
        direction = (1 if move_right else 0) - (1 if move_left else 0)
        if direction:
            self.facing = direction
            accel = ACCEL if self.on_ground else AIR_ACCEL
            self.vx += direction * accel * dt
            self.vx = max(-MOVE_SPEED, min(MOVE_SPEED, self.vx))
        else:
            drop = FRICTION * dt
            if abs(self.vx) <= drop:
                self.vx = 0.0
            else:
                self.vx -= drop * (1 if self.vx > 0 else -1)

        # ---- jump timing helpers
        self.coyote = COYOTE_TIME if self.on_ground else max(0.0, self.coyote - dt)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)

        if self.jump_buffer > 0 and self.coyote > 0:
            self.vy = JUMP_VELOCITY
            self.jump_buffer = 0.0
            self.coyote = 0.0
            self.on_ground = False
            self.riding = None

        # Releasing the key early cuts the jump short -> variable jump height
        if not jump_held and self.vy < JUMP_CUT:
            self.vy = JUMP_CUT

        # ---- gravity
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)

        # ---- move + collide, X first then Y (classic platformer order)
        self.x += self.vx * dt
        for r in solids:
            if self.overlaps(r):
                if self.vx > 0:
                    self.x = r[0] - self.w
                elif self.vx < 0:
                    self.x = r[0] + r[2]
                self.vx = 0.0

        was_airborne = not self.on_ground
        self.y += self.vy * dt
        self.on_ground = False
        self.riding = None
        for r in solids:
            if not self.overlaps(r):
                continue
            if self.vy > 0:
                self.y = r[1] - self.h
                self.vy = 0.0
                self.on_ground = True
                self.riding = r
            elif self.vy < 0:
                self.y = r[1] + r[3]
                self.vy = 0.0

        # ---- animation clock
        if self.on_ground and abs(self.vx) > 12:
            self.walk_phase += dt * (6.0 + abs(self.vx) / 60.0)
        elif self.on_ground:
            self.walk_phase = 0.0
        if was_airborne and self.on_ground:
            self.walk_phase = 0.0

    def bounce(self):
        self.vy = -560.0
        self.on_ground = False


class Slime(Entity):
    """A small patrolling blob.  Stomp it from above to pop it."""

    def __init__(self, x, y, left, right, speed=55.0):
        super().__init__(x, y, SLIME_W, SLIME_H)
        self.left_bound = float(left)
        self.right_bound = float(right)
        self.speed = speed
        self.direction = 1
        self.phase = random.uniform(0, math.tau)
        self.squash = 0.0          # 0..1, used for the hop animation

    def update(self, dt):
        self.x += self.direction * self.speed * dt
        if self.x <= self.left_bound:
            self.x = self.left_bound
            self.direction = 1
        elif self.x + self.w >= self.right_bound:
            self.x = self.right_bound - self.w
            self.direction = -1
        self.phase += dt * 5.5
        # little hop so the blob feels alive
        self.squash = max(0.0, math.sin(self.phase)) * 0.18

    def stomp(self):
        self.alive = False


class Coin(Entity):
    """A love token.  Bobs gently and spins (drawn narrower as it turns)."""

    def __init__(self, x, y, phase=0.0):
        super().__init__(x, y, TOKEN_SIZE, TOKEN_SIZE)
        self.phase = phase

    def update(self, dt):
        self.phase += dt * 3.2


class MovingPlatform(Entity):
    """A solid platform oscillating along one axis.

    ``update`` returns how far it moved this frame so the player can be
    carried along with it.
    """

    def __init__(self, x, y, w, h, axis="x", span=60.0, speed=1.2):
        super().__init__(x, y, w, h)
        self.origin = (float(x), float(y))
        self.axis = axis
        self.span = float(span)
        self.speed = float(speed)
        self.t = 0.0

    def update(self, dt):
        self.t += dt * self.speed
        offset = math.sin(self.t) * self.span
        nx = self.origin[0] + (offset if self.axis == "x" else 0.0)
        ny = self.origin[1] + (offset if self.axis == "y" else 0.0)
        dx, dy = nx - self.x, ny - self.y
        self.x, self.y = nx, ny
        return dx, dy


class Particle(Entity):
    """Confetti, dust puffs and sparkles."""

    def __init__(self, x, y, vx, vy, life, colour, size=5, gravity=900.0,
                 shape="square", spin=0.0):
        super().__init__(x, y, size, size)
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.colour = colour
        self.size = size
        self.gravity = gravity
        self.shape = shape
        self.spin = spin
        self.angle = random.uniform(0, 360)

    def update(self, dt):
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    @property
    def fade(self):
        """1.0 when fresh, 0.0 when about to disappear."""
        return max(0.0, min(1.0, self.life / self.max_life))


class Checkpoint(Entity):
    """A flag that becomes the new respawn point when touched."""

    def __init__(self, x, y, h=88):
        super().__init__(x, y, 26, h)
        self.activated = False
        self.wave = 0.0

    def update(self, dt):
        if self.activated:
            self.wave += dt * 4.0
