"""
Development helper (not part of the submitted game)
===================================================

Optional development tool - NOT part of the game, and NOT needed to run it.

This is the only file in the project that needs a third-party package
(Pillow), and it is only used to export still frames for review and for the
Padlet cover image.  The game itself never imports it.

The tkinter canvas is swapped for a tiny shim that records the same drawing
commands and replays them onto a Pillow image, so the exported PNG goes
through exactly the same layout code the player sees.

    python3 tools/render_preview.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from PIL import Image, ImageDraw, ImageFont

from game.app import LoveQuestApp
from game.settings import SCREEN_H, SCREEN_W, STEP

OUT_DIR = "/tmp/lq_preview"
FONT_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

STIPPLE_ALPHA = {"gray12": 0.13, "gray25": 0.25, "gray50": 0.5,
                 "gray75": 0.75, "gray100": 1.0}


class ShimCanvas:
    """Minimal stand-in for tkinter.Canvas that draws with Pillow."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.items = []
        self._next_id = 1

    # -- helpers ---------------------------------------------------------
    def _new(self, kind, coords, opts):
        tags = opts.get("tags", ())
        if isinstance(tags, str):
            tags = (tags,)
        item = {"id": self._next_id, "kind": kind, "coords": list(coords),
                "opts": dict(opts), "tags": tuple(tags)}
        self._next_id += 1
        self.items.append(item)
        return item["id"]

    def _find(self, ref):
        if isinstance(ref, int):
            return [i for i in self.items if i["id"] == ref]
        if ref == "all":
            return list(self.items)
        return [i for i in self.items if ref in i["tags"]]

    # -- tkinter API -----------------------------------------------------
    def create_rectangle(self, x1, y1, x2, y2, **kw):
        return self._new("rect", (x1, y1, x2, y2), kw)

    def create_oval(self, x1, y1, x2, y2, **kw):
        return self._new("oval", (x1, y1, x2, y2), kw)

    def create_polygon(self, *coords, **kw):
        if len(coords) == 1 and isinstance(coords[0], (list, tuple)):
            coords = coords[0]
        return self._new("poly", coords, kw)

    def create_line(self, *coords, **kw):
        if len(coords) == 1 and isinstance(coords[0], (list, tuple)):
            coords = coords[0]
        return self._new("line", coords, kw)

    def create_arc(self, x1, y1, x2, y2, **kw):
        return self._new("arc", (x1, y1, x2, y2), kw)

    def create_text(self, x, y, **kw):
        return self._new("text", (x, y), kw)

    def delete(self, ref):
        self.items = [i for i in self.items if i not in self._find(ref)]

    def move(self, ref, dx, dy):
        for item in self._find(ref):
            item["coords"] = [v + (dx if i % 2 == 0 else dy)
                              for i, v in enumerate(item["coords"])]

    def itemconfig(self, ref, **kw):
        for item in self._find(ref):
            item["opts"].update(kw)

    def coords(self, ref, *args):
        for item in self._find(ref):
            if args:
                item["coords"] = list(args)
            return item["coords"]
        return []

    def config(self, **kw):
        pass

    def tag_raise(self, *a):
        pass

    # -- rendering -------------------------------------------------------
    def _font(self, spec):
        size, bold = 14, False
        if isinstance(spec, (tuple, list)):
            if len(spec) > 1:
                size = int(spec[1])
            if len(spec) > 2:
                bold = "bold" in str(spec[2]).lower()
        try:
            return ImageFont.truetype(FONT_BOLD if bold else FONT_REG,
                                      max(6, int(size * 1.33)))
        except OSError:
            return ImageFont.load_default()

    def render(self):
        base = Image.new("RGB", (self.width, self.height), "#FFFFFF")
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for item in self.items:
            opts = item["opts"]
            fill = opts.get("fill", "")
            outline = opts.get("outline", "")
            width = int(opts.get("width", 1) or 1)
            alpha = STIPPLE_ALPHA.get(opts.get("stipple"), 1.0)
            if alpha < 1.0:
                # draw onto the overlay with reduced alpha
                layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
                ld = ImageDraw.Draw(layer)
                self._draw_item(ld, item, fill, outline, width, 255)
                mask = layer.split()[3].point(lambda a: int(a * alpha))
                layer.putalpha(mask)
                overlay = Image.alpha_composite(overlay, layer)
                draw = ImageDraw.Draw(overlay)
                continue
            self._draw_item(draw, item, fill, outline, width, 255)

        base = base.convert("RGBA")
        base = Image.alpha_composite(base, overlay)
        return base.convert("RGB")

    def _draw_item(self, d, item, fill, outline, width, alpha):
        kind, c = item["kind"], item["coords"]
        fill = fill or None
        outline = outline or None
        if kind == "rect":
            d.rectangle(c, fill=fill, outline=outline, width=width)
        elif kind == "oval":
            d.ellipse(c, fill=fill, outline=outline, width=width)
        elif kind == "poly":
            pts = [(c[i], c[i + 1]) for i in range(0, len(c) - 1, 2)]
            if len(pts) >= 3:
                d.polygon(pts, fill=fill, outline=outline, width=width)
        elif kind == "line":
            pts = [(c[i], c[i + 1]) for i in range(0, len(c) - 1, 2)]
            if len(pts) >= 2:
                d.line(pts, fill=fill, width=max(1, width), joint="curve")
                r = max(1, width // 2)
                for px, py in (pts[0], pts[-1]):
                    d.ellipse([px - r, py - r, px + r, py + r], fill=fill)
        elif kind == "arc":
            start = float(item["opts"].get("start", 0))
            extent = float(item["opts"].get("extent", 90))
            style = item["opts"].get("style", "pieslice")
            a0, a1 = -(start + extent), -start
            if style == "arc":
                d.arc(c, a0, a1, fill=outline or fill or "#000", width=max(1, width))
            elif style == "chord":
                d.chord(c, a0, a1, fill=fill, outline=outline)
            else:
                d.pieslice(c, a0, a1, fill=fill, outline=outline)
        elif kind == "text":
            font = self._font(item["opts"].get("font"))
            anchor = {"w": "lm", "e": "rm", "center": "mm",
                      "n": "ma", "s": "md"}.get(
                          item["opts"].get("anchor", "center"), "mm")
            d.text((c[0], c[1]), str(item["opts"].get("text", "")),
                   fill=fill or "#000000", font=font, anchor=anchor)


# --------------------------------------------------------------------------
def advance(app, seconds):
    """Let the bot run the level for a while so the shot looks natural."""
    from tools.autoplay import hazard_ahead, landing_ahead, solid_at
    steps = int(seconds / STEP)
    for _ in range(steps):
        solids = list(app.level.solids)
        for mover in app.movers:
            mover.update(STEP)
            solids.append(mover.rect)
        right, jump = True, False
        p = app.player
        if p.on_ground:
            wall = solid_at(solids, p.right + 6, p.bottom - 26)
            gap = not solid_at(solids, p.right + 30, p.bottom + 14)
            if wall or hazard_ahead(app.level.hazards, p):
                jump = True
            elif gap:
                if landing_ahead(solids, p):
                    jump = True
                else:
                    right = False
        if jump:
            p.request_jump()
        p.update(STEP, solids, False, right, True)
        app.level_time += STEP
        app.check_coins()
        app.check_slimes()
        app.check_checkpoints()
        app.update_camera(STEP)
        app.update_particles(STEP)


def shot(app, name):
    img = app.canvas.render()
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name + ".png")
    img.save(path)
    print("saved", path)


def main():
    root = tk.Tk()
    root.withdraw()
    app = LoveQuestApp(root, smoke=True)
    app.canvas = ShimCanvas(SCREEN_W, SCREEN_H)

    # 1. title
    app.state = "title"
    app.anim_t = 1.0
    app.render()
    shot(app, "01_title")

    # 2. level intro
    app.load_level(0)
    app.state = "intro"
    app.anim_t = 2.0
    app.render()
    shot(app, "02_intro")

    # 3. gameplay - one shot per level (hero placed on solid ground)
    spots = ((0, 1660, 400, "03_steppe"),
             (1, 1100, 480, "04_dusk"),
             (2, 700, 480, "05_castle"))
    for index, px, surface, name in spots:
        app.load_level(index)
        app.state = "intro"
        app.render()            # paint the level card (clears the canvas)
        app.begin_play()        # must rebuild the world behind it
        app.anim_t = 3.0
        app.player.x = px
        app.player.y = surface - 44
        app.player.on_ground = True
        app.player.walk_phase = 1.1
        app.player.invuln = 0
        app.player.tokens = 4
        app.level_time = 26.0
        cam = max(0.0, min(px - 420, app.level.width - SCREEN_W))
        app.camera_x = cam
        app.canvas.move("static", -cam, 0)
        app.canvas.move("bg", -cam * 0.45, 0)
        app.render()
        shot(app, name)

    # 4. pause overlay
    app.state = "paused"
    app.render()
    shot(app, "06_pause")

    # 5. level clear
    app.state = "levelclear"
    app.level_time = 78.0
    app.tokens_here = 11
    app.anim_t = 1.0
    app.render()
    shot(app, "07_levelclear")

    # 6. game over
    app.state = "gameover"
    app.render()
    shot(app, "08_gameover")

    # 7. ending dialogue
    app.enter_ending()
    app.run_time = 214.0
    app.run_tokens = 41
    app.cut_t = 9.2
    for _ in range(30):
        app.update_ending(STEP)
    app.render()
    shot(app, "09_ending")

    # 8. the finale
    app.cut_t = 15.6
    for _ in range(20):
        app.update_ending(STEP)
    app.spawn_firework(300, 160, 2)
    app.spawn_firework(720, 200, 2)
    for _ in range(40):
        app.update_ending(STEP)
    app.render()
    shot(app, "10_finale")

    # 9. credits
    app.enter_credits()
    app.anim_t = 1.0
    app.render()
    shot(app, "11_credits")

    app.running = False
    root.destroy()
    print("done")


if __name__ == "__main__":
    main()
