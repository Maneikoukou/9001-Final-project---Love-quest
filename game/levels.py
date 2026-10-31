"""
Level construction
==================

Levels are built with a tiny *builder API* instead of hand-drawn ASCII art.
Every call takes **tile** coordinates (1 tile = 40 px) which keeps the level
design readable and makes it trivial to nudge a platform by one square.

    level = Level("The Open Steppe", "Where the wind never stops", "steppe", 66)
    level.ground(0, 9, 12)        # solid ground from tile 0..9, surface row 12
    level.platform(35, 10, 3)     # 3-tile platform whose top is row 10
    level.coin_line(4, 10, 3)
    level.slime(16, 11)
    level.door(61, 11)            # castle door standing on row-11 ground

Rows run 0 (top of the screen) to 13 (bottom).  A 14-row level is exactly
560 px tall, which matches the window height, so a level scrolls only
horizontally.
"""

from .entities import Checkpoint, Coin, MovingPlatform, Slime
from .settings import (
    PLAYER_H, ROWS, SLIME_H, SLIME_W, TILE, TOKEN_SIZE,
)


class Level:
    """Static level data plus a factory that spawns fresh entities."""

    def __init__(self, name, subtitle, theme, width_tiles, tip=""):
        self.name = name
        self.subtitle = subtitle
        self.theme = theme
        self.tip = tip
        self.width = width_tiles * TILE
        self.solids = []        # (x, y, w, h) collision rectangles
        self.hazards = []       # (x, y, w, h) spikes
        self.decor = []         # (kind, x, y, scale) purely visual
        self.door_rect = None
        self.start_pos = (2 * TILE, 11 * TILE)
        self._coins = []
        self._slimes = []
        self._movers = []
        self._checkpoints = []

    # ------------------------------------------------------------ geometry
    def ground(self, x1, x2, top_row=12):
        """Solid block from tile ``x1`` to ``x2`` (inclusive) down to the floor."""
        self.solids.append((x1 * TILE, top_row * TILE,
                            (x2 - x1 + 1) * TILE, (ROWS - top_row) * TILE))
        return self

    def platform(self, x, row, w):
        """Floating platform, ``w`` tiles wide, 16 px thick."""
        self.solids.append((x * TILE, row * TILE, w * TILE, 16))
        return self

    def block(self, x, row, w=1, h=1):
        self.solids.append((x * TILE, row * TILE, w * TILE, h * TILE))
        return self

    def spikes(self, x, row, w=1):
        """A row of spikes sitting on the floor of the given tile row."""
        self.hazards.append((x * TILE, row * TILE + 16, w * TILE, 24))
        return self

    # ---------------------------------------------------------- collectables
    def coin(self, x, row):
        self._coins.append((x * TILE + (TILE - TOKEN_SIZE) / 2,
                            row * TILE + (TILE - TOKEN_SIZE) / 2))
        return self

    def coin_line(self, x, row, n, step=1):
        for i in range(n):
            self.coin(x + i * step, row)
        return self

    def coin_arc(self, x, row, n):
        """A little rainbow of coins - rewards a high jump."""
        for i in range(n):
            lift = i if i <= n // 2 else n - 1 - i
            self.coin(x + i, row - lift)
        return self

    # -------------------------------------------------------------- entities
    def slime(self, x, row, patrol=2):
        left = (x - patrol) * TILE
        right = (x + patrol + 1) * TILE
        self._slimes.append((x * TILE + (TILE - SLIME_W) / 2,
                             (row + 1) * TILE - SLIME_H, left, right))
        return self

    def mover(self, x, row, w=2, axis="x", span=60.0, speed=1.2):
        self._movers.append((x * TILE, row * TILE, w * TILE, 16, axis, span, speed))
        return self

    def checkpoint(self, x, row):
        self._checkpoints.append((x * TILE, (row + 1) * TILE - 88))
        return self

    def door(self, x, row):
        """Castle door: 2 tiles wide, 3 tiles tall, standing on tile row ``row``."""
        self.door_rect = (x * TILE, (row - 2) * TILE, 2 * TILE, 3 * TILE)
        return self

    def start(self, x, row):
        self.start_pos = (x * TILE + (TILE - 30) / 2, (row + 1) * TILE - PLAYER_H)
        return self

    # ------------------------------------------------------------- decoration
    def tree(self, x, row, scale=1.0):
        self.decor.append(("tree", x * TILE, (row + 1) * TILE, scale))
        return self

    def cloud(self, x, y, scale=1.0):
        self.decor.append(("cloud", x * TILE, y * TILE, scale))
        return self

    def bush(self, x, row, scale=1.0):
        self.decor.append(("bush", x * TILE, (row + 1) * TILE, scale))
        return self

    def castle(self, x, row, scale=1.0):
        self.decor.append(("castle", x * TILE, (row + 1) * TILE, scale))
        return self

    def rock(self, x, row, scale=1.0):
        self.decor.append(("rock", x * TILE, (row + 1) * TILE, scale))
        return self

    def turbine(self, x, scale=0.72):
        """A wind turbine on the skyline.

        Its rotor is animated, so it is drawn in the *dynamic* layer, which
        means it always paints on top of the ground.  Two rules follow from
        that: the feet sit on the near ridge rather than on the walkable
        grass (so the player running past reads as being in front of it), and
        they are kept a couple of tiles clear of platforms and spikes so a
        blade never crosses a ledge.
        """
        self.decor.append(("turbine", x * TILE, 11 * TILE + 6, scale))
        return self

    def sign(self, x, row, text):
        self.decor.append(("sign", x * TILE, (row + 1) * TILE, text))
        return self

    # --------------------------------------------------------------- spawning
    def spawn(self):
        """Return brand-new runtime objects so a level can be replayed."""
        coins = [Coin(cx, cy, phase=i * 0.5) for i, (cx, cy) in enumerate(self._coins)]
        slimes = [Slime(x, y, left, right) for (x, y, left, right) in self._slimes]
        movers = [MovingPlatform(x, y, w, h, axis, span, speed)
                  for (x, y, w, h, axis, span, speed) in self._movers]
        checkpoints = [Checkpoint(x, y) for (x, y) in self._checkpoints]
        return coins, slimes, movers, checkpoints

    @property
    def token_total(self):
        return len(self._coins)


# ===========================================================================
#  LEVEL 1 - The Open Steppe (gentle introduction)
# ===========================================================================
def build_steppe():
    lv = Level("The Open Steppe", "Where the wind never stops", "steppe", 66,
               tip="Arrow keys / A D to move    SPACE to jump")
    lv.start(2, 11)
    lv.ground(0, 9, 12)
    lv.coin_line(4, 10, 3)

    lv.ground(12, 20, 12)
    lv.slime(16, 11, 2)
    lv.coin(13, 10)
    lv.coin(14, 10)

    lv.ground(24, 33, 12)
    lv.slime(28, 11, 2)
    lv.coin_line(25, 10, 2)

    lv.platform(35, 10, 3)
    lv.coin_line(35, 9, 3)
    lv.platform(40, 10, 3)
    lv.coin(41, 9)

    lv.ground(45, 53, 12)
    lv.checkpoint(45, 11)
    lv.spikes(49, 11, 2)
    lv.coin(51, 10)
    lv.coin(52, 10)

    lv.ground(56, 65, 12)
    lv.coin_line(57, 10, 2)
    lv.door(61, 11)

    # scenery - no trees out here, just wind, rock and scrub
    for x, s in ((4, 1.15), (16, 0.95), (29, 1.05), (47, 0.90), (57, 1.0)):
        lv.turbine(x, s)
    for x, s in ((6, 0.9), (22, 1.0), (38, 0.8), (52, 0.9)):
        lv.bush(x, 11, s)
    for x, s in ((10, 1.0), (31, 0.8), (55, 1.1)):
        lv.rock(x, 11, s)
    # a wall of cumulus, the way the sky looks over open grassland
    for x, y, s in ((3, 2, 1.9), (14, 2, 2.2), (26, 1, 1.7), (38, 2, 2.0),
                    (50, 1, 1.8), (60, 2, 1.6),
                    (8, 4, 1.1), (20, 4, 0.95), (32, 5, 0.85),
                    (44, 4, 1.0), (56, 5, 0.9)):
        lv.cloud(x, y, s)
    lv.sign(3, 11, "START")
    return lv


# ===========================================================================
#  LEVEL 2 - The Dusk Crossing (moving platforms + more hazards)
# ===========================================================================
def build_dusk():
    lv = Level("The Dusk Crossing", "Mind the gap", "steppe_dusk", 72,
               tip="Stand on the glowing platforms - they carry you")
    lv.start(2, 11)
    lv.ground(0, 7, 12)
    lv.coin_line(3, 10, 3)

    lv.mover(9, 10, 2, "x", 70, 1.15)      # ferry across the first gap
    lv.coin(10, 8)

    lv.ground(13, 19, 12)
    lv.slime(15, 11, 2)
    lv.coin(17, 10)

    lv.platform(21, 10, 2)
    lv.platform(24, 9, 2)
    lv.coin(24, 8)

    lv.ground(27, 33, 12)
    lv.spikes(30, 11, 2)
    lv.coin(28, 10)

    lv.mover(35, 10, 2, "x", 55, 1.3)
    lv.coin(36, 8)

    lv.ground(38, 46, 12)
    lv.checkpoint(39, 11)
    lv.slime(43, 11, 2)
    lv.coin_line(41, 10, 2)

    lv.ground(50, 57, 12)
    lv.slime(52, 11, 1)
    lv.spikes(55, 11, 1)
    lv.coin(53, 9)

    lv.ground(61, 71, 12)
    lv.coin_line(62, 10, 2)
    lv.door(67, 11)

    for x, s in ((4, 1.00), (16, 1.10), (28, 0.90), (42, 1.05), (65, 0.85)):
        lv.turbine(x, s)
    for x, s in ((5, 0.9), (17, 0.8), (44, 0.9), (63, 0.8)):
        lv.bush(x, 11, s)
    for x, s in ((11, 1.0), (32, 0.9), (47, 1.1)):
        lv.rock(x, 11, s)
    for x, y, s in ((1, 2, 1.8), (14, 1, 1.6), (27, 2, 2.0), (40, 1, 1.5),
                    (52, 2, 1.9), (63, 1, 1.7),
                    (8, 4, 1.0), (22, 5, 0.9), (36, 4, 1.1),
                    (50, 5, 0.9), (62, 4, 0.95)):
        lv.cloud(x, y, s)
    lv.sign(3, 11, "BRIDGE")
    return lv


# ===========================================================================
#  LEVEL 3 - The Castle of Us (climb, then the gate)
# ===========================================================================
def build_castle():
    lv = Level("The Castle of Us", "She is waiting inside", "castle", 76,
               tip="Climb the keep - the door is at the far end")
    lv.start(2, 11)
    lv.ground(0, 9, 12)
    lv.spikes(6, 11, 2)
    lv.coin(4, 10)

    lv.ground(13, 19, 12)
    lv.slime(16, 11, 2)
    lv.coin_line(14, 10, 2)

    # --- the climb
    lv.platform(21, 10, 3)
    lv.coin(22, 9)
    lv.platform(25, 8, 3)
    lv.coin(26, 7)
    lv.platform(29, 6, 3)
    lv.coin_line(29, 5, 2)
    lv.mover(33, 5, 2, "y", 40, 1.4)
    lv.platform(37, 5, 4)
    lv.coin_line(38, 4, 3)
    lv.checkpoint(37, 4)

    # --- the descent
    lv.platform(43, 7, 3)
    lv.coin(44, 6)
    lv.platform(47, 9, 3)
    lv.coin(48, 8)

    lv.ground(50, 57, 12)
    lv.slime(53, 11, 2)
    lv.spikes(55, 11, 1)

    lv.ground(61, 75, 12)
    lv.coin_line(62, 10, 3)
    lv.castle(67, 11, 1.0)
    lv.door(69, 11)

    for x, y, s in ((2, 2, 1.0), (15, 1, 0.9), (30, 1, 1.1), (46, 2, 0.9),
                    (58, 1, 1.0), (10, 4, 0.70), (26, 5, 0.60),
                    (42, 4, 0.72), (58, 5, 0.62)):
        lv.cloud(x, y, s)
    for x in (5, 18, 52, 63):
        lv.tree(x, 11, 0.8)
    lv.sign(3, 11, "KEEP")
    return lv


def all_levels():
    """The campaign, in order."""
    return [build_steppe(), build_dusk(), build_castle()]
