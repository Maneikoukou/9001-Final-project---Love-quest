"""
Love Quest: A Castle for Two
============================

Global configuration for the game.

--------------------------------------------------------------------------
*** THIS IS THE ONLY FILE YOU NEED TO EDIT TO PERSONALISE THE GAME ***
Change the two names and the story lines below and the whole game becomes
yours.  Nothing else in the project has to be touched.
--------------------------------------------------------------------------

Author: Batiao
Unit:    COMP9001 - Introduction to Programming
"""

# ------------------------------------------------------------------ identity
APP_TITLE = "Love Quest: A Castle for Two"
PLAYER_NAME = "Batiao"      # protagonist
PARTNER_NAME = "Daisy"      # partner waiting at the castle

# What the hero wears.  "deel" is the long Mongolian robe (black cloth,
# silver trim, three toggles and a sash); "shirt" is the plain t-shirt and
# jeans the game shipped with.  Both are drawn from code, no images needed.
PLAYER_OUTFIT = "deel"

# Story text shown on the title screen, the level cards and the finale.
# Keep the lines short: they are rendered at a large font size.
STORY = {
    "tagline": "A tiny platformer about going the long way round for someone.",
    "intro": [
        "The castle gates are closed.",
        "Cross the three lands, gather love tokens,",
        "and find the one who is waiting for you.",
    ],
    "ending": [
        "You made it to the castle.",
        "Every jump. Every fall. All of it, for this.",
        '"I travelled a long way to ask you something..."',
        '"Will you marry me?"',
        "...",
        '"Yes. A thousand times, yes."',
    ],
    "credits": [
        "LOVE QUEST: A CASTLE FOR TWO",
        "",
        "Designed and programmed by " + PLAYER_NAME,
        "",
        "Starring " + PLAYER_NAME + " and " + PARTNER_NAME,
        "",
        "Made with Python + Tkinter GUI",
        "",
        "Thank you for playing.",
    ],
}

# ------------------------------------------------------------------- window
SCREEN_W = 1000
SCREEN_H = 560
TILE = 40                       # one level "tile" in pixels
ROWS = SCREEN_H // TILE         # 14 rows tall levels
FPS = 60
STEP = 1.0 / FPS                # fixed physics timestep
FONT = "Helvetica"              # maps to Arial on Windows

# ------------------------------------------------------------------ physics
# All values are in pixels and seconds, so the game feels the same on any
# machine no matter how fast it renders.
GRAVITY = 2300.0                # downward acceleration
JUMP_VELOCITY = -760.0          # initial upward speed  (~125 px = 3 tiles)
JUMP_CUT = -280.0               # velocity clamp when the jump key is released
MOVE_SPEED = 290.0              # top running speed
ACCEL = 2400.0                  # ground acceleration
AIR_ACCEL = 1700.0              # slightly weaker control in the air
FRICTION = 2800.0               # how quickly the player stops
MAX_FALL = 1100.0               # terminal velocity (stops tunnelling)
COYOTE_TIME = 0.10              # grace period after walking off a ledge
JUMP_BUFFER = 0.12              # remembers a jump pressed just before landing
STOMP_BOUNCE = -560.0           # bounce after squashing an enemy
KNOCKBACK_X = 260.0
KNOCKBACK_Y = -420.0

# ------------------------------------------------------------------- sizes
PLAYER_W, PLAYER_H = 30, 44
SLIME_W, SLIME_H = 38, 26
TOKEN_SIZE = 22
PLATFORM_THICKNESS = 16

# -------------------------------------------------------------------- rules
START_HEARTS = 3
MAX_HEARTS = 5
INVULN_TIME = 1.4               # seconds of blinking invincibility
TOKEN_POINTS = 10
TIME_BONUS_BASE = 300           # seconds
TIME_BONUS_RATE = 2             # points lost per second over the base
LEADERBOARD_SIZE = 5

# ------------------------------------------------------------------- colours
INK = "#2B2233"
CREAM = "#FFF6EE"
PANEL = "#FFFDF8"

THEMES = {
    # --------------------------------------------------------- open steppe
    # Every colour below was sampled from a photo of the Mongolian grassland
    # at midday: a deep navy zenith fading to a hazy pale horizon, huge white
    # cumulus, and olive-yellow grass that goes almost black in the shadows.
    "steppe": {
        "sky_top": "#1E3566",
        "sky_mid": "#4E7CAE",
        "sky_bottom": "#C2D4DE",
        "hill_far": "#6F7A55",
        "hill_near": "#5C6640",
        "ground_top": "#8E9A4E",
        "ground_top_line": "#6E7838",
        "ground_body": "#6B6238",
        "ground_body_dark": "#4A4526",
        "platform_top": "#8E9A4E",
        "platform_body": "#6B6238",
        "decor": "#4E5A30",
        "accent": "#FF7A9C",
        "cloud": "#FFFFFF",
        "slime": "#9A8FD8",
        "slime_dark": "#6E63B0",
        "mountain": "#9BABB2",
        "sun": "#FFFFFF",
        "shadow": "#414A22",
        "ground_tuft": "#B9C468",
        "ambient": "#F2F8FF",
        "backdrop": "rolling",      # low grassland ridges, not sharp peaks
        "cloud_shape": "cumulus",   # big fair-weather clouds
    },
    # ------------------------------------------------------- the same land
    # The identical grassland three hours later: the grass keeps its shape,
    # the light turns orange, the sky goes violet.  Re-using the terrain keys
    # is what makes level two feel like the same journey, not a new world.
    "steppe_dusk": {
        "sky_top": "#2B2A55",
        "sky_mid": "#B96A78",
        "sky_bottom": "#F7BE86",
        "hill_far": "#7A6A7E",
        "hill_near": "#4E4A45",
        "ground_top": "#7A7A46",
        "ground_top_line": "#5C5C33",
        "ground_body": "#5E5136",
        "ground_body_dark": "#3E3624",
        "platform_top": "#7A7A46",
        "platform_body": "#5E5136",
        "decor": "#454A2E",
        "accent": "#FFC46B",
        "cloud": "#F7C9A6",
        "slime": "#B98BC8",
        "slime_dark": "#8E63A8",
        "mountain": "#8A7690",
        "sun": "#FFD9A0",
        "shadow": "#3A3820",
        "ground_tuft": "#94914F",
        "ambient": "#FFD9A8",
        "backdrop": "rolling",
        "cloud_shape": "cumulus",
    },
    "castle": {
        "sky_top": "#2B2A4A",
        "sky_bottom": "#4B3F6B",
        "hill_far": "#3A3560",
        "hill_near": "#2E2A4D",
        "ground_top": "#8C8FB8",
        "ground_top_line": "#6B6E96",
        "ground_body": "#5A5C80",
        "ground_body_dark": "#454764",
        "platform_top": "#B4B8E2",
        "platform_body": "#6D6F95",
        "decor": "#2F6B57",
        "accent": "#FFD166",
        "cloud": "#6C6690",
        "slime": "#B7A6F0",
        "slime_dark": "#8E7BD1",
        "mountain": "#3B3663",
        "sun": "#DCE3FF",
        "shadow": "#3F4160",
        "ground_tuft": "#B9BEE6",
        "ambient": "#BFC4FF",
        "tufts": False,
    },
}

# Character colours (used by game/art.py)
SKIN = "#FFD9B8"
SKIN_SHADE = "#F0BFA0"
HAIR_PLAYER = "#3A2A20"
HAIR_PARTNER = "#5A3423"
SHIRT_PLAYER = "#FF6B8B"
SHIRT_PLAYER_DARK = "#E05073"
PANTS_PLAYER = "#3F5C8A"
SHOE = "#332B33"
DRESS_PARTNER = "#FFE1EC"
DRESS_PARTNER_DARK = "#F2BFD2"
BOW = "#FF5C8A"
HEART_FULL = "#FF5C8A"
HEART_EMPTY = "#E4D6DE"
STAR = "#FFC93C"
STAR_DARK = "#E0A417"

# The Mongolian deel.  Four near-blacks would collapse into one silhouette,
# so the robe gets a slightly lifted shade for folds and a cool grey for the
# piping - that grey is the only thing separating him from a night sky.
ROBE = "#1B1B22"
ROBE_SHADE = "#0D0D12"
ROBE_TRIM = "#7C7C8A"
ROBE_TRIM_LIGHT = "#C8C8D4"
SASH = "#2B2B35"
BOOT = "#0E0E12"
HAIR_DARK = "#15151A"
