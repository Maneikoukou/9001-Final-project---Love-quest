"""
Procedural artwork
==================

The game ships **zero image files** - every character, tree, cloud and
castle is drawn with tkinter canvas primitives (ovals, rounded polygons and
thick lines).  That keeps the project portable: only Python itself is needed,
and nothing can go missing from a zip file.

All helpers take a ``tags`` argument so the caller can group the shapes
(e.g. ``"dyn"`` for things redrawn every frame, ``"static"`` for the level,
``"bg"`` for the parallax scenery).

Depth is faked the only way tkinter allows: no alpha channel, so shadows are
solid darker tints of whatever sits underneath, and glow is built from a few
concentric discs that get lighter towards the edge.
"""

import math
import random

from .settings import (
    BOOT, BOW, DRESS_PARTNER, DRESS_PARTNER_DARK, HAIR_DARK, HAIR_PARTNER,
    HAIR_PLAYER, HEART_FULL, INK, PANTS_PLAYER, PLAYER_OUTFIT, ROBE,
    ROBE_SHADE, ROBE_TRIM, ROBE_TRIM_LIGHT, SASH, SHIRT_PLAYER,
    SHIRT_PLAYER_DARK, SHOE, SKIN, SKIN_SHADE, STAR, STAR_DARK,
)


# ------------------------------------------------------------------ colours
def _rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def blend(c1, c2, t):
    """Mix two ``#rrggbb`` colours.  ``t`` = 0 -> c1, 1 -> c2."""
    r1, g1, b1 = _rgb(c1)
    r2, g2, b2 = _rgb(c2)
    return "#%02x%02x%02x" % (int(r1 + (r2 - r1) * t),
                              int(g1 + (g2 - g1) * t),
                              int(b1 + (b2 - b1) * t))


# --------------------------------------------------------------- primitives
def heart_points(cx, cy, r, samples=40):
    """Polygon points for a heart of "radius" ``r`` centred on (cx, cy)."""
    points = []
    for i in range(samples):
        t = 2.0 * math.pi * i / samples
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        points.append(cx + x * r / 16.0)
        points.append(cy - y * r / 16.0)
    return points


def draw_heart(canvas, cx, cy, r, fill=HEART_FULL, outline="", width=0,
               tags=("dyn",)):
    return canvas.create_polygon(heart_points(cx, cy, r), fill=fill,
                                 outline=outline, width=width, tags=tags)


def star_points(cx, cy, r, inner=0.45, spikes=5, squash=1.0):
    """Star polygon.  ``squash`` < 1 narrows it horizontally (spin illusion)."""
    points = []
    for i in range(spikes * 2):
        angle = -math.pi / 2 + i * math.pi / spikes
        radius = r if i % 2 == 0 else r * inner
        points.append(cx + math.cos(angle) * radius * squash)
        points.append(cy + math.sin(angle) * radius)
    return points


def draw_star(canvas, cx, cy, r, fill=STAR, outline=STAR_DARK, width=2,
              tags=("dyn",), squash=1.0):
    return canvas.create_polygon(star_points(cx, cy, r, squash=squash),
                                 fill=fill, outline=outline, width=width,
                                 tags=tags)


def draw_token(canvas, cx, cy, r, phase, tags=("dyn",)):
    """A love token: soft glow, gold star, spin and a specular dot."""
    spin = abs(math.cos(phase))
    squash = 0.25 + 0.75 * spin
    # glow (three stacked discs, lighter as they get bigger)
    for k, light in ((1.34, 0.34), (1.14, 0.16)):
        canvas.create_oval(cx - r * k, cy - r * k, cx + r * k, cy + r * k,
                           fill=blend(STAR, "#FFFFFF", light), outline="",
                           tags=tags)
    draw_star(canvas, cx, cy, r, fill=STAR, outline=STAR_DARK, width=2,
              tags=tags, squash=squash)
    canvas.create_oval(cx - r * 0.30 * squash, cy - r * 0.34,
                       cx - r * 0.02 * squash, cy - r * 0.08,
                       fill="#FFF6C9", outline="", tags=tags)


def rounded_rect(canvas, x1, y1, x2, y2, r, fill, outline="", width=0,
                 tags=("dyn",)):
    """A rectangle with soft corners (built from a smoothed polygon)."""
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, fill=fill, outline=outline,
                                 width=width, smooth=True, tags=tags)


def draw_shadow(canvas, cx, cy, rx, ry, colour, tags=("dyn",)):
    """A flat ellipse on the ground - tkinter has no alpha, so the caller
    passes a colour that is a darker tint of the surface underneath."""
    return canvas.create_oval(cx - rx, cy - ry, cx + rx, cy + ry,
                              fill=colour, outline="", tags=tags)


# ------------------------------------------------------------------- people
def _draw_hero_head(canvas, cx, head_cy, s, facing, tags, hair, fringe=False):
    """The head, shared by both outfits so the hero stays the same person."""
    canvas.create_oval(cx - 10 * s, head_cy - 10 * s, cx + 10 * s,
                       head_cy + 10 * s, fill=SKIN, outline="", tags=tags)
    # hair cap - it has to reach the brow, otherwise the head reads as bald
    canvas.create_arc(cx - 10.5 * s, head_cy - 11 * s, cx + 10.5 * s,
                      head_cy + 5 * s, start=0, extent=180, fill=hair,
                      outline="", style="pieslice", tags=tags)
    # the lock that falls over the left of the forehead
    canvas.create_oval(cx - 10 * s, head_cy - 7 * s, cx - 2 * s,
                       head_cy - 1.0 * s, fill=hair, outline="", tags=tags)
    if fringe:
        # a shorter, side-parted lock on the right
        canvas.create_oval(cx - 1 * s, head_cy - 8 * s, cx + 9 * s,
                           head_cy - 2.5 * s, fill=hair, outline="", tags=tags)
    # sideburns
    for side in (-1, 1):
        canvas.create_oval(cx + side * 9.4 * s - 1.6 * s, head_cy - 5 * s,
                           cx + side * 9.4 * s + 1.6 * s, head_cy + 2 * s,
                           fill=hair, outline="", tags=tags)
    # hair highlight
    canvas.create_oval(cx - 7 * s, head_cy - 9.5 * s, cx - 2 * s,
                       head_cy - 6 * s, fill=blend(hair, "#FFFFFF", 0.3),
                       outline="", tags=tags)

    # --- face (shifted by facing direction)
    ex = cx + facing * 1.2 * s
    for side in (-1, 1):
        canvas.create_oval(ex + side * 4.2 * s - 1.4 * s, head_cy - 1 * s,
                           ex + side * 4.2 * s + 1.4 * s, head_cy + 2 * s,
                           fill=INK, outline="", tags=tags)
    canvas.create_arc(ex - 3.5 * s, head_cy + 2.5 * s, ex + 3.5 * s,
                      head_cy + 7 * s, start=200, extent=140, style="arc",
                      outline=INK, width=max(1, 1.4 * s), tags=tags)
    for side in (-1, 1):
        canvas.create_oval(ex + side * 7 * s - 2 * s, head_cy + 2 * s,
                           ex + side * 7 * s + 2 * s, head_cy + 4.5 * s,
                           fill="#FFB3C6", outline="", tags=tags)


def _draw_hero_deel(canvas, cx, feet, s, facing, phase, airborne, tags):
    """The hero in a Mongolian deel: long black robe, silver piping, three
    toggles on the chest and a sash at the waist.

    The robe hides the legs, so the walk cycle is carried by the hem swaying
    and by the sleeves instead of by the feet.
    """
    swing = math.sin(phase) * 6.0
    if airborne:
        swing = 4.0
    sway = swing * 0.32

    # --- boots, the only bit of leg the hem lets through
    for side, offset in ((-1, -swing), (1, swing)):
        bx = cx + side * 4.2 * s + offset * 0.3 * s
        canvas.create_oval(bx - 3.4 * s, feet - 4 * s, bx + 3.4 * s,
                           feet + 0.6 * s, fill=BOOT, outline="", tags=tags)

    # --- the robe itself: square shoulders flaring out to the ankles
    canvas.create_polygon(
        cx - 8 * s, feet - 27 * s, cx + 8 * s, feet - 27 * s,
        cx + 11 * s + sway * s, feet - 3 * s,
        cx - 11 * s + sway * s, feet - 3 * s,
        fill=ROBE, outline="", tags=tags)
    # one fold in shadow down the back half, so the robe is not a flat blob
    canvas.create_polygon(
        cx + 1.5 * s, feet - 27 * s, cx + 8 * s, feet - 27 * s,
        cx + 11 * s + sway * s, feet - 3 * s,
        cx + 3.5 * s + sway * s, feet - 3 * s,
        fill=ROBE_SHADE, outline="", tags=tags)
    # rim light on the leading edge.  A black robe against the castle's
    # night sky would otherwise read as a hole in the screen.
    canvas.create_polygon(
        cx - 8 * s, feet - 27 * s, cx - 6.6 * s, feet - 27 * s,
        cx - 9.6 * s + sway * s, feet - 3 * s,
        cx - 11 * s + sway * s, feet - 3 * s,
        fill=blend(ROBE, "#FFFFFF", 0.28), outline="", tags=tags)

    # --- silver band along the hem
    canvas.create_polygon(
        cx - 11 * s + sway * s, feet - 6 * s,
        cx + 11 * s + sway * s, feet - 6 * s,
        cx + 11 * s + sway * s, feet - 3 * s,
        cx - 11 * s + sway * s, feet - 3 * s,
        fill=ROBE_TRIM, outline="", tags=tags)

    # --- sash, with a small brass buckle sitting on the front
    canvas.create_rectangle(cx - 9.5 * s, feet - 18 * s, cx + 9.5 * s,
                            feet - 13 * s, fill=SASH, outline="", tags=tags)
    canvas.create_rectangle(cx - 9.5 * s, feet - 17.4 * s, cx + 9.5 * s,
                            feet - 16 * s,
                            fill=blend(SASH, "#FFFFFF", 0.22), outline="",
                            tags=tags)
    canvas.create_rectangle(cx + facing * 2 * s - 1.8 * s, feet - 17.4 * s,
                            cx + facing * 2 * s + 1.8 * s, feet - 13.6 * s,
                            fill="#8A6A2E", outline="", tags=tags)

    # --- the crossover placket: piping running from the left shoulder
    #     across to the right hip, the way a real deel fastens
    canvas.create_line(cx - 6.5 * s, feet - 25 * s, cx + 6.5 * s, feet - 17.5 * s,
                       fill=ROBE_TRIM, width=max(2, 2.4 * s), tags=tags)
    for tx, ty in ((-3.9, -23.5), (0.0, -21.25), (3.9, -19.0)):
        canvas.create_rectangle(cx + (tx - 2.2) * s, feet + (ty - 0.9) * s,
                                cx + (tx + 2.2) * s, feet + (ty + 0.9) * s,
                                fill=ROBE_TRIM_LIGHT, outline="", tags=tags)

    # --- wide sleeves with silver cuffs, then the hands
    for side in (-1, 1):
        shoulder = (cx + side * 8 * s, feet - 24 * s)
        hand = (cx + side * 11 * s - swing * 0.5 * s, feet - 12 * s)
        canvas.create_line(shoulder[0], shoulder[1], hand[0], hand[1],
                           fill=ROBE, width=max(3, 6.5 * s),
                           capstyle="round", tags=tags)
        canvas.create_oval(hand[0] - 3.4 * s, hand[1] - 3.4 * s,
                           hand[0] + 3.4 * s, hand[1] + 3.4 * s,
                           fill=ROBE_TRIM, outline="", tags=tags)
        canvas.create_oval(hand[0] - 2.3 * s, hand[1] - 2.3 * s,
                           hand[0] + 2.3 * s, hand[1] + 2.3 * s,
                           fill=SKIN, outline="", tags=tags)

    head_cy = feet - 33 * s
    _draw_hero_head(canvas, cx, head_cy, s, facing, tags, HAIR_DARK,
                    fringe=True)
    return head_cy


def _draw_hero_shirt(canvas, cx, feet, s, facing, phase, airborne, tags):
    """The original outfit: t-shirt, jeans, trainers."""
    swing = math.sin(phase) * 7.0
    if airborne:
        swing = 5.0

    # --- legs (drawn first so the torso overlaps them)
    leg_y0, leg_y1 = feet - 10 * s, feet - 2 * s
    for side, offset in ((-1, -swing), (1, swing)):
        hip_x = cx + side * 4.2 * s
        foot_x = hip_x + offset * 0.55 * s
        canvas.create_line(hip_x, leg_y0, foot_x, leg_y1, fill=PANTS_PLAYER,
                           width=max(2, 5 * s), capstyle="round", tags=tags)
        canvas.create_oval(foot_x - 4 * s, leg_y1 - 3 * s, foot_x + 4 * s,
                           leg_y1 + 2 * s, fill=SHOE, outline="", tags=tags)

    # --- torso
    rounded_rect(canvas, cx - 8 * s, feet - 25 * s, cx + 8 * s, feet - 8 * s,
                 4 * s, SHIRT_PLAYER, tags=tags)
    canvas.create_rectangle(cx - 8 * s, feet - 13 * s, cx + 8 * s, feet - 10 * s,
                            fill=SHIRT_PLAYER_DARK, outline="", tags=tags)

    # --- arms (on top so they are visible against the shirt)
    for side in (-1, 1):
        shoulder = (cx + side * 8 * s, feet - 23 * s)
        hand = (cx + side * 10 * s - swing * 0.5 * s, feet - 12 * s)
        canvas.create_line(shoulder[0], shoulder[1], hand[0], hand[1],
                           fill=SKIN, width=max(2, 4.5 * s),
                           capstyle="round", tags=tags)
        canvas.create_oval(hand[0] - 2.6 * s, hand[1] - 2.6 * s,
                           hand[0] + 2.6 * s, hand[1] + 2.6 * s,
                           fill=SKIN, outline="", tags=tags)

    head_cy = feet - 33 * s
    _draw_hero_head(canvas, cx, head_cy, s, facing, tags, HAIR_PLAYER)
    return head_cy


def draw_boy(canvas, cx, feet, s=1.0, facing=1, phase=0.0, airborne=False,
             tags=("dyn",), outfit=None):
    """The hero.  ``cx``/``feet`` is the bottom-centre of the sprite.

    ``outfit`` is ``"deel"`` (long Mongolian robe) or ``"shirt"``.  It
    defaults to ``PLAYER_OUTFIT`` in settings.py, so the whole game can be
    re-costumed by editing one line.
    """
    if (outfit or PLAYER_OUTFIT) == "deel":
        return _draw_hero_deel(canvas, cx, feet, s, facing, phase, airborne,
                               tags)
    return _draw_hero_shirt(canvas, cx, feet, s, facing, phase, airborne, tags)


def draw_girl(canvas, cx, feet, s=1.0, facing=-1, phase=0.0, airborne=False,
              tags=("dyn",)):
    """The partner.  Same skeleton as the hero, different silhouette."""
    swing = math.sin(phase) * 5.0

    # --- legs
    for side, offset in ((-1, -swing), (1, swing)):
        hip_x = cx + side * 3.5 * s
        foot_x = hip_x + offset * 0.4 * s
        canvas.create_line(hip_x, feet - 9 * s, foot_x, feet - 2 * s,
                           fill=SKIN_SHADE, width=max(2, 4 * s),
                           capstyle="round", tags=tags)
        canvas.create_oval(foot_x - 3.5 * s, feet - 3.5 * s, foot_x + 3.5 * s,
                           feet + 1.5 * s, fill="#C86A8E", outline="",
                           tags=tags)

    # --- dress
    canvas.create_polygon(
        cx - 5 * s, feet - 26 * s, cx + 5 * s, feet - 26 * s,
        cx + 12 * s, feet - 7 * s, cx - 12 * s, feet - 7 * s,
        fill=DRESS_PARTNER, outline="", tags=tags)
    canvas.create_polygon(
        cx - 12 * s, feet - 9 * s, cx + 12 * s, feet - 9 * s,
        cx + 12 * s, feet - 7 * s, cx - 12 * s, feet - 7 * s,
        fill=DRESS_PARTNER_DARK, outline="", tags=tags)
    canvas.create_oval(cx - 4 * s, feet - 24 * s, cx + 4 * s, feet - 20 * s,
                       fill=BOW, outline="", tags=tags)

    # --- arms, on top of the dress
    for side in (-1, 1):
        hand_x = cx + side * 11 * s - swing * 0.4 * s
        canvas.create_line(cx + side * 7 * s, feet - 23 * s,
                           hand_x, feet - 14 * s,
                           fill=SKIN, width=max(2, 4 * s),
                           capstyle="round", tags=tags)
        canvas.create_oval(hand_x - 2.4 * s, feet - 16.4 * s,
                           hand_x + 2.4 * s, feet - 11.6 * s,
                           fill=SKIN, outline="", tags=tags)

    # --- hair behind the head
    canvas.create_oval(cx - 11 * s, feet - 42 * s, cx + 11 * s, feet - 20 * s,
                       fill=HAIR_PARTNER, outline="", tags=tags)

    # --- head
    head_cy = feet - 33 * s
    canvas.create_oval(cx - 9.5 * s, head_cy - 9.5 * s, cx + 9.5 * s,
                       head_cy + 9.5 * s, fill=SKIN, outline="", tags=tags)
    # fringe
    canvas.create_arc(cx - 10 * s, head_cy - 11 * s, cx + 10 * s,
                      head_cy + 8 * s, start=10, extent=160, fill=HAIR_PARTNER,
                      outline="", style="pieslice", tags=tags)
    # long side strands
    for side in (-1, 1):
        canvas.create_oval(cx + side * 9 * s - 3.5 * s, head_cy - 4 * s,
                           cx + side * 9 * s + 3.5 * s, feet - 16 * s,
                           fill=HAIR_PARTNER, outline="", tags=tags)

    # --- face
    ex = cx + facing * 1.2 * s
    for side in (-1, 1):
        canvas.create_oval(ex + side * 4 * s - 1.3 * s, head_cy - 1 * s,
                           ex + side * 4 * s + 1.3 * s, head_cy + 2 * s,
                           fill=INK, outline="", tags=tags)
    canvas.create_arc(ex - 3 * s, head_cy + 2.5 * s, ex + 3 * s,
                      head_cy + 6.5 * s, start=200, extent=140, style="arc",
                      outline=INK, width=max(1, 1.3 * s), tags=tags)
    for side in (-1, 1):
        canvas.create_oval(ex + side * 6.5 * s - 2 * s, head_cy + 2 * s,
                           ex + side * 6.5 * s + 2 * s, head_cy + 4.5 * s,
                           fill="#FFA8BE", outline="", tags=tags)
    # hair bow
    canvas.create_polygon(cx + 7 * s, head_cy - 9 * s, cx + 13 * s,
                          head_cy - 12 * s, cx + 13 * s, head_cy - 5 * s,
                          fill=BOW, outline="", tags=tags)
    canvas.create_polygon(cx + 7 * s, head_cy - 9 * s, cx + 2 * s,
                          head_cy - 12 * s, cx + 2 * s, head_cy - 5 * s,
                          fill=BOW, outline="", tags=tags)
    return head_cy


# ---------------------------------------------------------------- backdrop
def draw_sun(canvas, cx, cy, r, colour, tags=("sky",)):
    """A disc with a fake glow: concentric rings that fade towards white."""
    for k, light in ((1.60, 0.52), (1.30, 0.34), (1.10, 0.18)):
        canvas.create_oval(cx - r * k, cy - r * k, cx + r * k, cy + r * k,
                           fill=blend(colour, "#FFFFFF", light), outline="",
                           tags=tags)
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=colour,
                       outline="", tags=tags)


def draw_stars(canvas, width, count, colour, tags=("sky",), seed=7):
    """Scatter for the night sky."""
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.uniform(0, width)
        y = rng.uniform(20, 300)
        r = rng.uniform(1.0, 2.4)
        canvas.create_oval(x - r, y - r, x + r, y + r, fill=colour,
                           outline="", tags=tags)


def draw_mountains(canvas, width, bottom, base_y, colour, tags=("bg",)):
    """Overlapping triangles far behind the playfield."""
    rng = random.Random(11)
    x = -320.0
    while x < width + 400:
        w = rng.uniform(300, 470)
        h = rng.uniform(120, 205)
        canvas.create_polygon(x, base_y, x + w / 2, base_y - h, x + w, base_y,
                              fill=colour, outline="", tags=tags)
        x += w * 0.58


def draw_hill_layer(canvas, width, bottom, base_y, amp, period, colour,
                    tags=("bg",), phase=0.0, step=26, rim=True):
    """One parallax ridge: a sine-sum silhouette instead of flat circles.

    ``rim=False`` drops the sunlit edge.  The farthest ridge wants that: a
    bright line on the horizon reads as a wire, not as haze.
    """
    points = []
    x = -260.0
    while x < width + 520:
        y = (base_y
             - amp * (0.55 + 0.45 * math.sin(x / period + phase))
             - amp * 0.22 * math.sin(x / (period * 0.41) + phase * 1.7))
        points.extend([x, y])
        x += step
    points.extend([width + 520, bottom + 20, -260, bottom + 20])
    # rim light: the same silhouette lifted a few pixels, in a lighter shade.
    # Skipped for dark night-time silhouettes, where it would read as a wire.
    r, g, b = _rgb(colour)
    if rim and (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.35:
        rim_points = []
        for i in range(0, len(points), 2):
            rim_points.extend([points[i], points[i + 1] - 5])
        canvas.create_polygon(rim_points, fill=blend(colour, "#FFFFFF", 0.20),
                              outline="", tags=tags)
    canvas.create_polygon(points, fill=colour, outline="", tags=tags)


def draw_depth_fade(canvas, width, top, bottom, colour, tags=("bg",), bands=7):
    """Darken everything below ``top`` so gaps read as deep pits rather than
    as more walkable ground."""
    deep = blend(colour, "#10241A", 0.45)
    step = (bottom - top) / bands
    for i in range(bands):
        t = (i + 1) / bands
        canvas.create_rectangle(-260, top + i * step, width + 520,
                                top + (i + 1) * step + 1,
                                fill=blend(colour, deep, t * t),
                                outline="", tags=tags)


def draw_cloud(canvas, x, y, s, colour, tags=("bg",)):
    shade = blend(colour, "#C9C2D8", 0.35)
    for dx, dy, r in ((2, 8, 15), (16, 4, 19), (33, 8, 15)):
        canvas.create_oval(x + dx * s - r * s, y + dy * s - r * s,
                           x + dx * s + r * s, y + dy * s + r * s,
                           fill=shade, outline="", tags=tags)
    for dx, dy, r in ((0, 0, 18), (16, -7, 22), (34, 0, 16), (18, 8, 18)):
        canvas.create_oval(x + dx * s - r * s, y + dy * s - r * s,
                           x + dx * s + r * s, y + dy * s + r * s,
                           fill=colour, outline="", tags=tags)


def draw_cumulus(canvas, x, y, s, colour, tags=("bg",)):
    """A fair-weather cumulus, the kind that fills a grassland sky.

    Two passes only: a blue-grey slab that becomes the shaded flat base, then
    the sunlit puffs piled on top of it.  The base shows through the gaps
    between the puffs, which is what gives the cloud its volume without any
    real transparency.
    """
    shade = blend(colour, "#9FB0C6", 0.34)
    canvas.create_oval(x - 54 * s, y - 14 * s, x + 54 * s, y + 14 * s,
                       fill=shade, outline="", tags=tags)
    for dx, dy, r in ((-40, -6, 24), (-16, -23, 31), (12, -19, 27),
                      (37, -7, 23), (-2, -3, 25)):
        canvas.create_oval(x + (dx - r) * s, y + (dy - r) * s,
                           x + (dx + r) * s, y + (dy + r) * s,
                           fill=colour, outline="", tags=tags)
    # a couple of brighter bumps so the crown catches the sun
    for dx, dy, r in ((-16, -38, 13), (16, -30, 10)):
        canvas.create_oval(x + (dx - r) * s, y + (dy - r) * s,
                           x + (dx + r) * s, y + (dy + r) * s,
                           fill=blend(colour, "#FFFFFF", 0.6), outline="",
                           tags=tags)


def draw_turbine(canvas, x, feet, s, angle, tags=("dyn",)):
    """A wind turbine - the one landmark that says "this is the steppe".

    The tower is a tapered white mast; the three blades rotate around the
    hub by ``angle`` radians.  It is drawn in the dynamic layer, so the rotor
    really does turn instead of being a frozen stamp.
    """
    mast = "#E7ECF3"
    mast_shade = "#AEB9C9"
    hub_y = feet - 86 * s

    canvas.create_oval(x - 8 * s, feet - 2 * s, x + 8 * s, feet + 4 * s,
                       fill="#4A4A32", outline="", tags=tags)
    canvas.create_polygon(x - 3.0 * s, feet, x - 1.5 * s, hub_y,
                          x + 1.5 * s, hub_y, x + 3.0 * s, feet,
                          fill=mast, outline="", tags=tags)
    canvas.create_polygon(x + 0.5 * s, feet, x + 0.8 * s, hub_y,
                          x + 1.5 * s, hub_y, x + 3.0 * s, feet,
                          fill=mast_shade, outline="", tags=tags)

    for i in range(3):
        a = angle + i * (2.0 * math.pi / 3.0)
        canvas.create_line(x, hub_y,
                           x + math.cos(a) * 34 * s,
                           hub_y + math.sin(a) * 34 * s,
                           fill=mast, width=max(2, int(3.4 * s)),
                           capstyle="round", tags=tags)
    canvas.create_oval(x - 3.4 * s, hub_y - 3.4 * s, x + 3.4 * s,
                       hub_y + 3.4 * s, fill=mast_shade, outline="", tags=tags)


def draw_rock(canvas, x, feet, s, theme, tags=("static",)):
    """A weathered boulder - the steppe has no trees, so it needs something
    to break up the horizon."""
    base = blend(theme["ground_body"], "#2A2418", 0.25)
    light = blend(base, "#FFFFFF", 0.26)
    for dx, dy, rx, ry in ((-8, -6, 11, 7), (8, -5, 9, 6), (0, -13, 8, 6)):
        canvas.create_oval(x + (dx - rx) * s, feet + (dy - ry) * s,
                           x + (dx + rx) * s, feet + (dy + ry) * s,
                           fill=base, outline="", tags=tags)
    canvas.create_oval(x - 9 * s, feet - 18 * s, x + 1 * s, feet - 12 * s,
                       fill=light, outline="", tags=tags)


# ------------------------------------------------------------------ terrain
def draw_ground_block(canvas, x, y, w, h, theme, tags=("static",)):
    """A chunk of earth: gradient soil, pebbles, rounded grass cap, tufts."""
    # a grassy bank with the soil showing through near the bottom
    cap = min(54.0, max(26.0, h * 0.58))
    top = y + cap
    bands = max(2, int((h - cap) / 12))
    for i in range(bands):
        y0 = top + (h - cap) * i / bands
        y1 = top + (h - cap) * (i + 1) / bands + 1
        canvas.create_rectangle(
            x, y0, x + w, y1,
            fill=blend(theme["ground_body"], theme["ground_body_dark"],
                       i / max(1, bands - 1)),
            outline="", tags=tags)

    # pebbles - seeded so the pattern is stable between redraws
    rng = random.Random(int(x) * 31 + int(w))
    for _ in range(int(w // 40)):
        px = x + rng.uniform(8, max(10, w - 14))
        py = top + rng.uniform(8, max(12, h - cap - 14))
        r = rng.uniform(2.2, 4.6)
        canvas.create_oval(px, py, px + r * 2.1, py + r * 1.5,
                           fill=theme["ground_body_dark"], outline="",
                           tags=tags)

    # grass cap with rounded top corners
    rounded_rect(canvas, x, y, x + w, y + cap, 9, theme["ground_top"],
                 tags=tags)
    canvas.create_rectangle(x, y + 14, x + w, y + cap,
                            fill=theme["ground_top"], outline="", tags=tags)
    # sunlit lip along the very top
    canvas.create_rectangle(x, y + 6, x + w, y + 10,
                            fill=blend(theme["ground_top"], "#FFFFFF", 0.22),
                            outline="", tags=tags)
    canvas.create_rectangle(x, y + cap - 5, x + w, y + cap + 1,
                            fill=theme["ground_top_line"], outline="",
                            tags=tags)

    # tufts poking above the surface
    if not theme.get("tufts", True):
        return
    px = x + 12
    i = 0
    while px < x + w - 10:
        hgt = 8 if i % 2 == 0 else 4
        canvas.create_polygon(px - 4, y + 2, px, y - hgt, px + 4, y + 2,
                              fill=theme["ground_tuft"], outline="",
                              tags=tags)
        px += 27
        i += 1


def draw_platform(canvas, x, y, w, h, theme, tags=("static",)):
    """A floating ledge: shadow underneath, soil body, grass cap, tufts."""
    canvas.create_rectangle(x + 8, y + h, x + w - 8, y + h + 5,
                            fill=theme["shadow"], outline="", tags=tags)
    rounded_rect(canvas, x, y, x + w, y + h, 8, theme["platform_body"],
                 tags=tags)
    canvas.create_rectangle(x, y + h - 3, x + w, y + h,
                            fill=blend(theme["platform_body"], "#000000", 0.18),
                            outline="", tags=tags)
    rounded_rect(canvas, x, y, x + w, y + 11, 8, theme["platform_top"],
                 tags=tags)

    if not theme.get("tufts", True):
        return
    px = x + 13
    i = 0
    while px < x + w - 9:
        hgt = 8 if i % 2 == 0 else 4
        canvas.create_polygon(px - 3.5, y + 2, px, y - hgt, px + 3.5, y + 2,
                              fill=theme["ground_tuft"], outline="", tags=tags)
        px += 25
        i += 1


def draw_tree(canvas, x, feet, s, theme, tags=("static",)):
    trunk = "#8B5E3C"
    dark = "#6E4529"
    canvas.create_polygon(x - 9 * s, feet, x - 5 * s, feet - 62 * s,
                          x + 5 * s, feet - 62 * s, x + 9 * s, feet,
                          fill=trunk, outline="", tags=tags)
    canvas.create_polygon(x + 1 * s, feet, x + 2 * s, feet - 62 * s,
                          x + 5 * s, feet - 62 * s, x + 9 * s, feet,
                          fill=dark, outline="", tags=tags)

    base = theme["decor"]
    light = blend(base, "#FFFFFF", 0.26)
    for dx, dy, r in ((0, -78, 34), (-25, -60, 23), (25, -60, 23),
                      (-14, -92, 20), (17, -92, 20)):
        canvas.create_oval(x + dx * s - r * s, feet + dy * s - r * s,
                           x + dx * s + r * s, feet + dy * s + r * s,
                           fill=base, outline="", tags=tags)
    for dx, dy, r in ((-10, -92, 12), (11, -84, 9)):
        canvas.create_oval(x + dx * s - r * s, feet + dy * s - r * s,
                           x + dx * s + r * s, feet + dy * s + r * s,
                           fill=light, outline="", tags=tags)


def draw_bush(canvas, x, feet, s, theme, tags=("static",)):
    base = theme["hill_near"]
    light = blend(base, "#FFFFFF", 0.22)
    for dx, r in ((-15, 13), (0, 17), (15, 12)):
        canvas.create_oval(x + (dx - r) * s, feet - 2 * r * s,
                           x + (dx + r) * s, feet + 2 * s,
                           fill=base, outline="", tags=tags)
    canvas.create_oval(x - 6 * s, feet - 24 * s, x + 6 * s, feet - 12 * s,
                       fill=light, outline="", tags=tags)


def draw_castle(canvas, x, feet, s, theme, tags=("static",)):
    """A big friendly castle silhouette drawn behind the goal door."""
    stone = theme["ground_body"]
    stone_dark = theme["ground_body_dark"]
    roof = theme["accent"]
    body_w, body_h = 260 * s, 240 * s
    left = x - body_w / 2

    canvas.create_rectangle(left, feet - body_h, left + body_w, feet,
                            fill=stone, outline="", tags=tags)
    # crenellations
    for i in range(7):
        bx = left + i * (body_w / 7)
        canvas.create_rectangle(bx, feet - body_h - 18 * s,
                                bx + body_w / 14, feet - body_h,
                                fill=stone_dark, outline="", tags=tags)
    # towers
    for side in (-1, 1):
        tx = x + side * body_w * 0.42
        canvas.create_rectangle(tx - 34 * s, feet - body_h - 60 * s,
                                tx + 34 * s, feet, fill=stone_dark,
                                outline="", tags=tags)
        canvas.create_polygon(tx - 44 * s, feet - body_h - 60 * s, tx,
                              feet - body_h - 130 * s, tx + 44 * s,
                              feet - body_h - 60 * s, fill=roof, outline="",
                              tags=tags)
        canvas.create_rectangle(tx - 8 * s, feet - body_h - 30 * s,
                                tx + 8 * s, feet - body_h - 6 * s,
                                fill=theme["sky_top"], outline="", tags=tags)
    # windows
    for i in range(4):
        wx = left + body_w * (0.18 + i * 0.21)
        canvas.create_oval(wx - 12 * s, feet - body_h * 0.72,
                           wx + 12 * s, feet - body_h * 0.72 + 26 * s,
                           fill=theme["accent"], outline="", tags=tags)
    # banner
    canvas.create_rectangle(x - 3 * s, feet - body_h - 120 * s, x + 3 * s,
                            feet - body_h, fill=stone_dark, outline="",
                            tags=tags)
    canvas.create_polygon(x + 3 * s, feet - body_h - 120 * s,
                          x + 46 * s, feet - body_h - 104 * s,
                          x + 3 * s, feet - body_h - 88 * s,
                          fill=theme["accent"], outline="", tags=tags)
    draw_heart(canvas, x + 18 * s, feet - body_h - 104 * s, 9 * s,
               fill="#FFFFFF", tags=tags)


def draw_door(canvas, rect, theme, open_=True, tags=("static",)):
    """The castle gate.  Glows warmly when the level can be finished."""
    x, y, w, h = rect
    canvas.create_rectangle(x - 6, y - 6, x + w + 6, y + h,
                            fill=theme["ground_body_dark"], outline="",
                            tags=tags)
    canvas.create_arc(x, y, x + w, y + w, start=0, extent=180,
                      fill=theme["ground_body"], outline="", tags=tags)
    canvas.create_rectangle(x, y + w / 2, x + w, y + h,
                            fill="#2A2233" if open_ else "#120E18",
                            outline="", tags=tags)
    if open_:
        canvas.create_rectangle(x + 6, y + w / 2 + 6, x + w - 6, y + h,
                                fill="#FFE9A8", outline="", tags=tags)
        for i in range(3):
            canvas.create_line(x + w / 2, y + h - 10 - i * 12,
                               x + w / 2, y + h - 18 - i * 12,
                               fill="#F6C86A", width=3, tags=tags)
    canvas.create_oval(x + w / 2 - 3, y + w / 2 + 10, x + w / 2 + 3,
                       y + w / 2 + 16, fill="#B08A3E", outline="", tags=tags)
    draw_heart(canvas, x + w / 2, y - 14, 10, fill=theme["accent"], tags=tags)


def draw_spikes(canvas, rect, colour="#D6DAF0", tags=("static",)):
    x, y, w, h = rect
    canvas.create_rectangle(x, y + h - 5, x + w, y + h, fill="#8A8DA8",
                            outline="", tags=tags)
    count = max(1, int(w // 20))
    step = w / count
    for i in range(count):
        sx = x + i * step
        canvas.create_polygon(sx, y + h - 3, sx + step / 2, y, sx + step,
                              y + h - 3, fill=colour, outline="#9A9DB8",
                              width=1, tags=tags)
        canvas.create_line(sx + step / 2, y + 3, sx + step / 2, y + h - 6,
                           fill="#FFFFFF", width=1, tags=tags)


def draw_sign(canvas, x, feet, text, theme, tags=("static",)):
    canvas.create_rectangle(x - 2, feet - 46, x + 2, feet, fill="#8B5E3C",
                            outline="", tags=tags)
    canvas.create_rectangle(x - 34, feet - 62, x + 34, feet - 40,
                            fill="#F2DDB6", outline="#8B5E3C", width=2,
                            tags=tags)
    canvas.create_text(x, feet - 51, text=text, fill=INK,
                       font=("Helvetica", 9, "bold"), tags=tags)


def draw_slime(canvas, x, y, w, h, squash, colour, dark, facing=1,
               tags=("dyn",)):
    """A wobbly blob with eyes and a glossy highlight."""
    lift = squash * h * 0.5
    canvas.create_oval(x, y + lift, x + w, y + h, fill=colour, outline="",
                       tags=tags)
    canvas.create_oval(x + w * 0.14, y + lift + h * 0.10,
                       x + w * 0.40, y + lift + h * 0.30,
                       fill="#FFFFFF", outline="", tags=tags)
    eye_x = x + w * (0.36 if facing > 0 else 0.44)
    for offset in (0.0, 0.16):
        canvas.create_oval(eye_x + w * offset, y + h * 0.34,
                           eye_x + w * (offset + 0.14), y + h * 0.58,
                           fill=INK, outline="", tags=tags)
        canvas.create_oval(eye_x + w * (offset + 0.03), y + h * 0.38,
                           eye_x + w * (offset + 0.07), y + h * 0.45,
                           fill="#FFFFFF", outline="", tags=tags)
    canvas.create_oval(x, y + h * 0.78, x + w, y + h, fill=dark, outline="",
                       tags=tags)
