"""
Love Quest - game application
=============================

This module owns the window, the fixed-timestep game loop and a small
**state machine** that decides what the player is looking at:

    title  ->  intro  ->  play  <->  paused
                          |
                          +--> levelclear --> intro (next level)
                          +--> gameover  --> play (retry)
                          +--> ending    --> credits --> title

Rendering is split in two halves:

* the **static** layer (sky, ground, platforms, scenery) is drawn once per
  level and then simply slid sideways as the camera moves - cheap and smooth;
* the **dynamic** layer (player, enemies, tokens, particles) is redrawn
  every frame.

Everything is drawn with tkinter primitives, so the project needs no
external libraries and no image assets.
"""

import math
import random
import time
import tkinter as tk

from . import art
from .entities import Particle, Player
from .levels import all_levels
from .save_system import SaveSystem, format_time
from .settings import (
    APP_TITLE, FONT, FPS, HEART_EMPTY, HEART_FULL, INK, LEADERBOARD_SIZE,
    MAX_HEARTS, PANEL, PARTNER_NAME, PLAYER_H, PLAYER_NAME, SCREEN_H,
    SCREEN_W, STAR, STEP, STORY, THEMES, TIME_BONUS_BASE, TIME_BONUS_RATE,
    TOKEN_POINTS,
)


# --------------------------------------------------------------------------
#  small colour helpers
# --------------------------------------------------------------------------
def lerp_colour(c1, c2, t):
    """Blend two ``#rrggbb`` colours, ``t`` = 0 -> c1, 1 -> c2."""
    return art.blend(c1, c2, t)


class LoveQuestApp:
    """The whole game."""

    # ------------------------------------------------------------------ setup
    def __init__(self, root, smoke=False):
        self.root = root
        self.smoke = smoke
        self.root.title(APP_TITLE)
        self.root.resizable(False, False)
        self.root.configure(bg="#1B1B2F")

        self.canvas = tk.Canvas(root, width=SCREEN_W, height=SCREEN_H,
                                highlightthickness=0, bg="#1B1B2F")
        self.canvas.pack()

        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.save = SaveSystem.load()
        self.levels = all_levels()
        self.level_index = 0
        self.level = self.levels[0]
        self.theme = THEMES[self.level.theme]

        self.keys = set()
        self.jump_held = False
        self.state = "title"
        self.frame = 0
        self.anim_t = 0.0
        self.running = True

        # play state
        self.player = None
        self.coins = []
        self.slimes = []
        self.movers = []
        self.checkpoints = []
        self.particles = []
        self.ambient = []
        self.turbines = []
        self.camera_x = 0.0
        self.level_time = 0.0
        self.run_time = 0.0
        self.run_tokens = 0
        self.hud = {}

        # ending state
        self.cut_t = 0.0
        self.firework_timer = 0.0

        self._last = time.perf_counter()
        self._accumulator = 0.0

        self.enter_title()
        if not smoke:
            self.tick()

    # ------------------------------------------------------------------ loop
    def tick(self):
        """Fixed timestep loop: physics always advances at 1/60 s."""
        if not self.running:
            return
        now = time.perf_counter()
        elapsed = now - self._last
        self._last = now
        if elapsed > 0.25:          # window was dragged / laptop slept
            elapsed = 0.25
        self._accumulator += elapsed

        steps = 0
        while self._accumulator >= STEP and steps < 6:
            self.update(STEP)
            self._accumulator -= STEP
            steps += 1

        self.frame += 1
        self.render()
        self.root.after(max(1, int(1000 / FPS) - 2), self.tick)

    def update(self, dt):
        self.anim_t += dt
        if self.state == "play":
            self.update_play(dt)
        elif self.state == "ending":
            self.update_ending(dt)

    # ----------------------------------------------------------------- input
    def on_key_down(self, event):
        key = event.keysym.lower()
        if key in self.keys:
            return                      # ignore auto-repeat
        self.keys.add(key)

        if key in ("space", "w", "up"):
            self.jump_held = True

        # --- menus first, so SPACE does not also make the hero jump
        if self.state == "title":
            if key in ("return", "space"):
                self.start_game()
            return
        if self.state == "intro":
            if key in ("return", "space"):
                self.begin_play()
            elif key == "escape":
                self.enter_title()
            return
        if self.state == "levelclear":
            if key in ("return", "space"):
                self.next_level()
            return
        if self.state == "gameover":
            if key in ("return", "r", "space"):
                self.retry_level()
            elif key == "escape":
                self.enter_title()
            return
        if self.state == "ending":
            if key in ("return", "space"):
                if self.cut_t < 14.4:
                    self.cut_t = 14.4        # skip to the finale
                else:
                    self.enter_credits()
            return
        if self.state == "credits":
            if key in ("return", "space"):
                self.enter_title()
            return

        # --- gameplay
        if self.state == "play":
            if key == "escape":
                self.state = "paused"
                self.jump_held = False
                return
            if key in ("space", "w", "up") and self.player:
                self.player.request_jump()
        elif self.state == "paused":
            if key == "escape":
                # remove the pause card before handing control back
                self.canvas.delete("ui")
                self.state = "play"
            elif key == "q":
                self.enter_title()

    def on_key_up(self, event):
        key = event.keysym.lower()
        self.keys.discard(key)
        if key in ("space", "w", "up"):
            self.jump_held = False

    def on_close(self):
        self.running = False
        self.root.destroy()

    # ------------------------------------------------------------- navigation
    def enter_title(self):
        self.state = "title"
        self.jump_held = False
        self.canvas.delete("all")

    def start_game(self):
        self.run_time = 0.0
        self.run_tokens = 0
        self.load_level(0)
        self.state = "intro"

    def load_level(self, index):
        self.level_index = index
        self.level = self.levels[index]
        self.theme = THEMES[self.level.theme]
        (self.coins, self.slimes,
         self.movers, self.checkpoints) = self.level.spawn()
        self.player = Player(*self.level.start_pos)
        self.particles = []
        self.camera_x = 0.0
        self.level_time = 0.0
        self.tokens_here = 0
        self.ambient = self.make_ambient()
        self.turbines = self.collect_turbines()
        self.canvas.delete("all")
        self.draw_level_static()
        self.build_hud()

    def collect_turbines(self):
        """Pull the wind turbines out of the decoration list.

        They are the only piece of scenery whose rotor moves, so they cannot
        be baked into the static layer; the renderer redraws them each frame.
        Each one gets a slightly different phase and speed, otherwise a row
        of rotors turning in lockstep looks mechanical.
        """
        turbines = []
        for kind, x, y, s in self.level.decor:
            if kind != "turbine":
                continue
            i = len(turbines)
            turbines.append({"x": x, "y": y, "s": s,
                             "phase": i * 1.7,
                             "speed": 0.55 + 0.2 * (i % 3)})
        return turbines

    def make_ambient(self):
        """Slow-drifting motes that give each level a bit of atmosphere."""
        rng = random.Random(self.level_index * 977 + 13)
        return [{
            "x": rng.uniform(0, self.level.width),
            "y": rng.uniform(70, 430),
            "r": rng.uniform(1.1, 2.4),
            "phase": rng.uniform(0, math.tau),
            "speed": rng.uniform(0.45, 1.3),
        } for _ in range(30)]

    def begin_play(self):
        """Leave the level card and rebuild the world underneath it.

        The intro screen paints over the whole canvas, so the pre-drawn level
        has to be drawn again here - otherwise the player would start running
        around on top of the level card with no ground in sight.
        """
        self.state = "play"
        self.camera_x = 0.0
        self.canvas.delete("all")
        self.draw_level_static()
        self.build_hud()
        self._last = time.perf_counter()
        self._accumulator = 0.0

    def next_level(self):
        if self.level_index + 1 < len(self.levels):
            self.load_level(self.level_index + 1)
            self.state = "intro"
        else:
            self.enter_ending()

    def retry_level(self):
        self.load_level(self.level_index)
        self.state = "play"
        self._last = time.perf_counter()
        self._accumulator = 0.0

    def game_over(self):
        self.state = "gameover"
        self.jump_held = False

    def enter_ending(self):
        self.state = "ending"
        self.cut_t = 0.0
        self.particles = []
        self.firework_timer = 0.0
        self.save.finished = True
        SaveSystem.add_score(self.save, PLAYER_NAME,
                             max(1.0, self.run_time), self.run_tokens)
        self.canvas.delete("all")

    def enter_credits(self):
        self.state = "credits"
        self.canvas.delete("all")

    # --------------------------------------------------------------- gameplay
    def update_play(self, dt):
        player = self.player
        if player is None:
            return

        self.level_time += dt
        self.run_time += dt

        # --- moving platforms first, then carry whoever stands on them
        solids = list(self.level.solids)
        for mover in self.movers:
            dx, dy = mover.update(dt)
            standing_on_it = (
                player.on_ground
                and abs(player.bottom - mover.y) <= 8
                and player.right > mover.x + 2
                and player.left < mover.x + mover.w - 2
            )
            if standing_on_it:
                player.x += dx
                player.y += dy
            solids.append(mover.rect)

        left = bool(self.keys & {"left", "a"})
        right = bool(self.keys & {"right", "d"})
        player.update(dt, solids, left, right, self.jump_held)

        self.update_camera(dt)
        self.check_coins()
        self.check_slimes()
        self.check_hazards()
        self.check_checkpoints()
        self.check_goal()
        self.check_pit()
        self.update_particles(dt)

    def update_camera(self, dt):
        target = self.player.center_x - SCREEN_W * 0.42
        target = max(0.0, min(target, self.level.width - SCREEN_W))
        dx = (target - self.camera_x) * min(1.0, dt * 9.0)
        if abs(target - self.camera_x) < 0.4:
            dx = target - self.camera_x
        self.camera_x += dx
        # slide the pre-drawn layers instead of rebuilding them
        self.canvas.move("static", -dx, 0)
        self.canvas.move("bg", -dx * 0.45, 0)
        self.canvas.move("bg2", -dx * 0.62, 0)

    def check_coins(self):
        for coin in self.coins:
            if not coin.alive:
                continue
            coin.update(STEP)
            if self.player.overlaps(coin.rect):
                coin.alive = False
                self.player.tokens += 1
                self.tokens_here += 1
                self.run_tokens += 1
                self.burst(coin.center_x, coin.center_y, 5, STAR, 90)

    def check_slimes(self):
        player = self.player
        for slime in self.slimes:
            if not slime.alive:
                continue
            slime.update(STEP)
            if not player.overlaps(slime.rect):
                continue
            falling = player.vy > 120
            above = player.bottom - slime.top < 26
            if falling and above:
                slime.stomp()
                player.bounce()
                self.burst(slime.center_x, slime.center_y, 10, "#9BE3A8", 150)
            else:
                self.damage(slime.center_x)

    def check_hazards(self):
        for hazard in self.level.hazards:
            if self.player.overlaps(hazard):
                self.damage(self.player.center_x - 1)
                return

    def check_checkpoints(self):
        for cp in self.checkpoints:
            cp.update(STEP)
            if cp.activated or not self.player.overlaps(cp.rect):
                continue
            cp.activated = True
            self.player.spawn = (cp.x - 4, cp.y + cp.h - PLAYER_H)
            self.burst(cp.center_x, cp.y + 10, 8, "#FFD166", 160)

    def check_goal(self):
        if self.level.door_rect and self.player.overlaps(self.level.door_rect):
            self.complete_level()

    def check_pit(self):
        if self.player.y < SCREEN_H + 120:
            return
        if self.player.invuln <= 0:
            self.player.hearts -= 1
        if self.player.hearts <= 0:
            self.game_over()
        else:
            self.player.respawn()

    def damage(self, from_x=None):
        player = self.player
        if player.invuln > 0:
            return
        still_alive = player.hurt(from_x)
        self.burst(player.center_x, player.center_y, 8, "#FF6B8B", 180)
        if not still_alive:
            self.game_over()

    def complete_level(self):
        """Reached the door: record the time and show the summary card."""
        seconds = self.level_time
        self.save.record_time(self.level.name, seconds)
        self.save.total_tokens += self.tokens_here
        SaveSystem.save(self.save)
        self.burst(self.player.center_x, self.player.center_y, 16, "#FFD166", 260)
        if self.level_index + 1 >= len(self.levels):
            self.enter_ending()
        else:
            self.state = "levelclear"
            self.jump_held = False

    # -------------------------------------------------------------- particles
    def burst(self, x, y, count, colour, speed):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            power = random.uniform(0.3, 1.0) * speed
            self.particles.append(Particle(
                x, y, math.cos(angle) * power, math.sin(angle) * power - 60,
                random.uniform(0.4, 0.9), colour,
                size=random.randint(3, 7),
                shape=random.choice(("square", "circle")),
                spin=random.uniform(-360, 360)))

    def spawn_firework(self, cx, cy, depth):
        """Recursive confetti burst.

        Base case: ``depth < 0``.  Every burst throws ten particles and then
        splits into two smaller, offset bursts - a compact demonstration of
        recursion used for something visible.
        """
        if depth < 0:
            return
        colours = ("#FF6B8B", "#FFD166", "#8FD6F2", "#B7A6F0", "#9BE3A8")
        for _ in range(10):
            angle = random.uniform(0, math.tau)
            power = random.uniform(80, 260)
            self.particles.append(Particle(
                cx, cy, math.cos(angle) * power, math.sin(angle) * power,
                random.uniform(1.0, 2.0), random.choice(colours),
                size=random.randint(4, 9), gravity=520.0,
                shape=random.choice(("square", "circle")),
                spin=random.uniform(-420, 420)))
        if depth > 0:
            for _ in range(2):
                self.spawn_firework(cx + random.uniform(-170, 170),
                                    cy + random.uniform(-90, 60), depth - 1)

    def update_particles(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive][-260:]

    # ------------------------------------------------------------------ HUD
    def hud_panel(self, x1, y1, x2, y2, r=14):
        """A cream panel with a soft drop shadow."""
        art.rounded_rect(self.canvas, x1 + 2, y1 + 3, x2 + 2, y2 + 3, r,
                         "#E4D6E3", tags=("hud",))
        art.rounded_rect(self.canvas, x1, y1, x2, y2, r, PANEL,
                         outline="#F1E4EE", width=1, tags=("hud",))

    def build_hud(self):
        c = self.canvas
        c.delete("hud")
        self.hud = {}

        # --- hearts + tokens
        self.hud_panel(14, 12, 306, 62)
        self.hud["hearts"] = [
            art.draw_heart(c, 40 + i * 24, 37, 10, HEART_FULL, tags=("hud",))
            for i in range(MAX_HEARTS)
        ]
        c.create_line(166, 24, 166, 50, fill="#EEDFE9", tags=("hud",))
        self.hud["star"] = art.draw_star(c, 188, 37, 10, tags=("hud",))
        self.hud["tokens"] = c.create_text(
            204, 37, text="0", anchor="w", fill=INK,
            font=(FONT, 15, "bold"), tags=("hud",))

        # --- personal best
        self.hud_panel(694, 12, 986, 62)
        best = self.save.best_time(self.level.name)
        c.create_text(712, 30, text="BEST", anchor="w", fill="#B29CB8",
                      font=(FONT, 9, "bold"), tags=("hud",))
        self.hud["best"] = c.create_text(
            712, 48, text=format_time(best), anchor="w", fill=INK,
            font=(FONT, 13, "bold"), tags=("hud",))
        art.draw_heart(c, 954, 37, 9, fill="#FFC2D6", tags=("hud",))

        # --- level name + timer
        self.hud_panel(352, 12, 648, 62)
        self.hud["level"] = c.create_text(
            SCREEN_W / 2, 26, text=self.level.name.upper(), fill="#B29CB8",
            font=(FONT, 9, "bold"), tags=("hud",))
        self.hud["timer"] = c.create_text(
            SCREEN_W / 2, 45, text="0:00", fill=INK,
            font=(FONT, 16, "bold"), tags=("hud",))

    def refresh_hud(self):
        if not self.hud:
            return
        player = self.player
        for i, item in enumerate(self.hud["hearts"]):
            filled = i < player.hearts
            self.canvas.itemconfig(item, fill=HEART_FULL if filled else HEART_EMPTY)
        self.canvas.itemconfig(self.hud["tokens"], text=str(player.tokens))
        self.canvas.itemconfig(self.hud["timer"], text=format_time(self.level_time))

    # ---------------------------------------------------------------- render
    def render(self):
        if self.state in ("play", "paused"):
            self.render_world()
            if self.state == "paused":
                self.render_pause_overlay()
        elif self.state == "title":
            self.render_title()
        elif self.state == "intro":
            self.render_intro()
        elif self.state == "levelclear":
            self.render_levelclear()
        elif self.state == "gameover":
            self.render_gameover()
        elif self.state == "ending":
            self.render_ending()
        elif self.state == "credits":
            self.render_credits()

    # -- level construction (drawn once) -----------------------------------
    def gradient(self, top, bottom, bands=80, tags=(), mid=None):
        """Smooth vertical gradient - many thin bands instead of 14 fat ones.

        ``mid`` inserts a third colour stop halfway down.  Two stops are
        enough for a UI panel but a sky needs the middle stop, otherwise the
        ramp spends the whole screen in the dark and never gets bright where
        the eye expects the horizon to be.
        """
        step = SCREEN_H / bands
        for i in range(bands):
            t = i / (bands - 1)
            if mid is None:
                colour = lerp_colour(top, bottom, t)
            elif t < 0.5:
                colour = lerp_colour(top, mid, t * 2.0)
            else:
                colour = lerp_colour(mid, bottom, (t - 0.5) * 2.0)
            self.canvas.create_rectangle(
                0, i * step, SCREEN_W, (i + 1) * step + 1,
                fill=colour, outline="", tags=tags)

    def draw_level_static(self):
        c = self.canvas
        theme = self.theme
        c.delete("all")

        # sky gradient
        self.gradient(theme["sky_top"], theme["sky_bottom"], tags=("sky",),
                      mid=theme.get("sky_mid"))

        # sun or moon, pinned to the screen (it is "infinitely" far away)
        if self.level.theme == "castle":
            art.draw_stars(c, self.level.width, 80, "#E8E4FF", tags=("sky",))
            art.draw_sun(c, SCREEN_W * 0.82, 88, 26, theme["sun"], tags=("sky",))
        else:
            art.draw_sun(c, SCREEN_W * 0.84, 104, 22, theme["sun"],
                         tags=("sky",))

        # Layers of depth behind the playfield.  A grassland has long rolling
        # ridges rather than peaks, so a "rolling" backdrop swaps the mountain
        # triangles for one more very soft band near the horizon.
        if theme.get("backdrop") == "rolling":
            art.draw_hill_layer(c, self.level.width, SCREEN_H, 396, 34, 640,
                                theme["mountain"], tags=("bg",), phase=1.1,
                                step=34, rim=False)
            art.draw_hill_layer(c, self.level.width, SCREEN_H, 430, 56, 300,
                                theme["hill_far"], tags=("bg",), phase=0.0)
        else:
            art.draw_mountains(c, self.level.width, SCREEN_H, 460,
                               theme["mountain"], tags=("bg",))
            art.draw_hill_layer(c, self.level.width, SCREEN_H, 430, 56, 300,
                                theme["hill_far"], tags=("bg",), phase=0.0)
        art.draw_hill_layer(c, self.level.width, SCREEN_H, 478, 40, 190,
                            theme["hill_near"], tags=("bg",), phase=2.3)
        art.draw_depth_fade(c, self.level.width, 482, SCREEN_H + 30,
                            theme["hill_near"], tags=("bg",))

        # scenery
        cumulus = theme.get("cloud_shape") == "cumulus"
        for kind, x, y, extra in self.level.decor:
            if kind == "cloud":
                if cumulus:
                    art.draw_cumulus(c, x, y, extra, theme["cloud"],
                                     tags=("bg2",))
                else:
                    art.draw_cloud(c, x, y, extra, theme["cloud"],
                                   tags=("bg2",))
            elif kind == "tree":
                art.draw_tree(c, x, y, extra, theme)
            elif kind == "bush":
                art.draw_bush(c, x, y, extra, theme)
            elif kind == "rock":
                art.draw_rock(c, x, y, extra, theme)
            elif kind == "castle":
                art.draw_castle(c, x, y, extra, theme)
            elif kind == "sign":
                art.draw_sign(c, x, y, extra, theme)
            # "turbine" is animated, so render_world draws it instead

        # solids
        for (x, y, w, h) in self.level.solids:
            if h <= 20:
                art.draw_platform(c, x, y, w, h, theme)
            else:
                art.draw_ground_block(c, x, y, w, h, theme)

        # spikes
        for hazard in self.level.hazards:
            art.draw_spikes(c, hazard, "#D6DAF0", tags=("static",))

        # the gate
        if self.level.door_rect:
            art.draw_door(c, self.level.door_rect, theme, open_=True,
                          tags=("static",))

    # -- the live world ----------------------------------------------------
    def render_world(self):
        c = self.canvas
        theme = self.theme
        cam = self.camera_x
        c.delete("dyn")
        solids = list(self.level.solids) + [m.rect for m in self.movers]

        # --- wind turbines.  The rotors turn, so they live in the dynamic
        #     layer; painting them first keeps the player in front of them.
        for t in self.turbines:
            sx = t["x"] - cam
            if sx < -70 or sx > SCREEN_W + 70:
                continue
            art.draw_turbine(c, sx, t["y"], t["s"],
                             self.anim_t * t["speed"] + t["phase"])

        # --- drifting pollen / fireflies (parallax 0.85)
        for mote in self.ambient:
            mx = mote["x"] - cam * 0.85 + math.sin(
                self.anim_t * 0.55 * mote["speed"] + mote["phase"]) * 16
            if mx < -12 or mx > SCREEN_W + 12:
                continue
            my = mote["y"] + math.sin(
                self.anim_t * 0.9 * mote["speed"] + mote["phase"] * 1.7) * 11
            r = mote["r"]
            c.create_oval(mx - r, my - r, mx + r, my + r,
                          fill=theme["ambient"], outline="", tags=("dyn",))

        # checkpoints
        for cp in self.checkpoints:
            sx = cp.x - cam
            if sx < -80 or sx > SCREEN_W + 80:
                continue
            pole = theme["ground_body_dark"]
            art.draw_shadow(c, sx + 14, cp.y + cp.h, 16, 4, theme["shadow"])
            c.create_rectangle(sx + 2, cp.y, sx + 6, cp.y + cp.h,
                               fill=pole, outline="", tags=("dyn",))
            flag = "#FFD166" if cp.activated else "#D9D2DE"
            wave = math.sin(cp.wave) * 4 if cp.activated else 0
            c.create_polygon(sx + 6, cp.y + 4,
                             sx + 34 + wave, cp.y + 14,
                             sx + 6, cp.y + 26,
                             fill=flag, outline="", tags=("dyn",))
            c.create_polygon(sx + 6, cp.y + 4, sx + 34 + wave, cp.y + 14,
                             sx + 6, cp.y + 15,
                             fill=art.blend(flag, "#FFFFFF", 0.35), outline="",
                             tags=("dyn",))

        # moving platforms
        for mover in self.movers:
            sx = mover.x - cam
            art.draw_platform(c, sx, mover.y, mover.w, mover.h, theme,
                              tags=("dyn",))

        # love tokens
        for coin in self.coins:
            if not coin.alive:
                continue
            sx = coin.x - cam
            if sx < -40 or sx > SCREEN_W + 40:
                continue
            bob = math.sin(coin.phase) * 3
            art.draw_token(c, sx + coin.w / 2, coin.y + coin.h / 2 + bob,
                           10, coin.phase, tags=("dyn",))

        # slimes
        for slime in self.slimes:
            if not slime.alive:
                continue
            sx = slime.x - cam
            if sx < -60 or sx > SCREEN_W + 60:
                continue
            art.draw_shadow(c, sx + slime.w / 2, slime.bottom + 1,
                            slime.w * 0.46, 5, theme["shadow"])
            art.draw_slime(c, sx, slime.y, slime.w, slime.h, slime.squash,
                           theme["slime"], theme["slime_dark"],
                           facing=slime.direction, tags=("dyn",))

        # particles
        for p in self.particles:
            sx = p.x - cam
            if p.shape == "circle":
                c.create_oval(sx, p.y, sx + p.size, p.y + p.size,
                              fill=p.colour, outline="", tags=("dyn",))
            else:
                c.create_rectangle(sx, p.y, sx + p.size, p.y + p.size,
                                   fill=p.colour, outline="", tags=("dyn",))

        # the hero (shadow first, then the sprite)
        player = self.player
        if player is not None:
            px = player.x - cam
            ground = self.surface_below(player.center_x, player.bottom, solids)
            if ground is not None:
                drop = max(0.0, ground - player.bottom)
                k = max(0.35, 1.0 - drop / 340.0)
                art.draw_shadow(c, px + player.w / 2, ground - 1,
                                15 * k, 5 * k, theme["shadow"])

            blink = player.invuln > 0 and int(self.anim_t * 16) % 2 == 0
            if not blink:
                bob = 0.0
                if player.on_ground and abs(player.vx) > 20:
                    bob = abs(math.sin(player.walk_phase)) * 2.0
                art.draw_boy(c, px + player.w / 2,
                             player.y + player.h - bob, 1.0, player.facing,
                             player.walk_phase, not player.on_ground,
                             tags=("dyn",))

        # damage flash
        if player is not None and player.hurt_flash > 0:
            c.create_rectangle(0, 0, SCREEN_W, SCREEN_H, fill="#FF5C7A",
                               outline="", stipple="gray12", tags=("dyn",))

        # the HUD is built once, so everything dynamic above would otherwise
        # paint over it
        c.tag_raise("hud")
        self.refresh_hud()

    def surface_below(self, x, y, solids):
        """Y coordinate of the first solid surface under (x, y), or None."""
        best = None
        for (sx, sy, sw, sh) in solids:
            if sx <= x <= sx + sw and sy >= y - 2:
                if best is None or sy < best:
                    best = sy
        return best

    # -- overlays ----------------------------------------------------------
    def dim(self, alpha=0.55):
        self.canvas.create_rectangle(0, 0, SCREEN_W, SCREEN_H,
                                     fill="#1B1424", outline="",
                                     stipple="gray50", tags=("ui",))

    def render_pause_overlay(self):
        c = self.canvas
        c.delete("ui")
        self.dim()
        art.rounded_rect(c, 340, 190, 660, 370, 22, PANEL,
                         outline="#E8D8E4", width=2, tags=("ui",))
        c.create_text(500, 240, text="PAUSED", fill=INK,
                      font=(FONT, 26, "bold"), tags=("ui",))
        c.create_text(500, 285, text="ESC  -  resume", fill=INK,
                      font=(FONT, 14), tags=("ui",))
        c.create_text(500, 312, text="Q  -  quit to title", fill=INK,
                      font=(FONT, 14), tags=("ui",))
        c.create_text(500, 345, text=f"Tokens  {self.player.tokens}",
                      fill="#9C8AA0", font=(FONT, 12), tags=("ui",))

    def render_title(self):
        c = self.canvas
        c.delete("all")
        # dreamy vertical gradient
        self.gradient("#FFE3EF", "#DCEBFF")
        # floating hearts
        for i in range(9):
            phase = self.anim_t * 0.55 + i * 0.9
            hx = 70 + (i * 113) % (SCREEN_W - 140)
            hy = SCREEN_H - ((phase * 46) % (SCREEN_H + 120))
            size = 8 + (i % 3) * 5
            art.draw_heart(c, hx + math.sin(phase) * 16, hy, size,
                           fill="#FFC2D6", tags=("ui",))

        c.create_text(SCREEN_W / 2, 128, text="LOVE QUEST",
                      fill="#4A3350", font=(FONT, 54, "bold"))
        c.create_text(SCREEN_W / 2, 180, text="A CASTLE FOR TWO",
                      fill="#A97FA8", font=(FONT, 17, "bold"))
        c.create_text(SCREEN_W / 2, 220, text=STORY["tagline"],
                      fill="#6B5570", font=(FONT, 13))

        # the two heroes, standing on soft shadows
        for hx, rx in ((392, 62), (608, 66)):
            c.create_oval(hx - rx, 412, hx + rx, 432, fill="#DDE0F2",
                          outline="")
        art.draw_boy(c, 392, 418, 2.6, facing=1, phase=0.0, tags=("ui",))
        art.draw_girl(c, 608, 418, 2.6, facing=-1, phase=0.0, tags=("ui",))

        for i in range(3):
            art.draw_heart(c, 500, 268 + i * 30,
                           10 - i * 2 + math.sin(self.anim_t * 3 + i) * 1.6,
                           fill="#FF7FA5", tags=("ui",))

        pulse = 0.5 + 0.5 * math.sin(self.anim_t * 3.4)
        c.create_text(SCREEN_W / 2, 470, text="PRESS  ENTER  TO  START",
                      fill=lerp_colour("#B0557E", "#FF5C8A", pulse),
                      font=(FONT, 19, "bold"))

        art.rounded_rect(c, 300, 492, 700, 532, 12, "#FFFFFF",
                         outline="#F0D7E4", width=2, tags=("ui",))
        c.create_text(SCREEN_W / 2, 512,
                      text="Arrows / A D  move      SPACE  jump      ESC  pause",
                      fill="#7A6480", font=(FONT, 11, "bold"), tags=("ui",))

        if self.save.finished:
            c.create_text(SCREEN_W / 2, 550, text="* you have finished the story *",
                          fill="#B08A3E", font=(FONT, 11, "bold"), tags=("ui",))

    def render_intro(self):
        c = self.canvas
        c.delete("all")
        theme = self.theme
        self.gradient(theme["sky_top"], theme["sky_bottom"],
                      mid=theme.get("sky_mid"))

        art.rounded_rect(c, 150, 110, 850, 450, 24, PANEL,
                         outline="#E8D8E4", width=3, tags=("ui",))
        c.create_text(SCREEN_W / 2, 156,
                      text=f"LEVEL {self.level_index + 1} / {len(self.levels)}",
                      fill="#B08AA0", font=(FONT, 12, "bold"), tags=("ui",))
        c.create_text(SCREEN_W / 2, 206, text=self.level.name,
                      fill=INK, font=(FONT, 34, "bold"), tags=("ui",))
        c.create_text(SCREEN_W / 2, 246, text=self.level.subtitle,
                      fill="#7A6480", font=(FONT, 14), tags=("ui",))

        art.rounded_rect(c, 210, 282, 790, 328, 12, "#FFF3F7",
                         outline="#F3D9E4", width=2, tags=("ui",))
        c.create_text(SCREEN_W / 2, 305, text=self.level.tip,
                      fill="#8A6A80", font=(FONT, 12, "bold"), tags=("ui",))

        c.create_text(SCREEN_W / 2, 360,
                      text=f"{self.level.token_total} love tokens hidden in this land",
                      fill="#8A6A80", font=(FONT, 12), tags=("ui",))

        pulse = 0.5 + 0.5 * math.sin(self.anim_t * 3.4)
        c.create_text(SCREEN_W / 2, 408, text="PRESS  ENTER  TO  BEGIN",
                      fill=lerp_colour("#B0557E", "#FF5C8A", pulse),
                      font=(FONT, 17, "bold"), tags=("ui",))
        c.create_text(SCREEN_W / 2, 470,
                      text="ESC  -  back to title", fill="#B7A4BC",
                      font=(FONT, 11), tags=("ui",))

    def render_levelclear(self):
        c = self.canvas
        c.delete("all")
        self.gradient("#FFF0F5", "#E7F3FF")
        for i in range(10):
            art.draw_heart(c, 90 + i * 96, 90 + math.sin(self.anim_t * 2 + i) * 12,
                           10, fill="#FFC2D6", tags=("ui",))

        art.rounded_rect(c, 190, 130, 810, 470, 24, PANEL,
                         outline="#F0D7E4", width=3, tags=("ui",))
        c.create_text(SCREEN_W / 2, 180, text="LAND  CLEARED",
                      fill="#B0557E", font=(FONT, 30, "bold"), tags=("ui",))
        c.create_text(SCREEN_W / 2, 222, text=self.level.name,
                      fill=INK, font=(FONT, 16), tags=("ui",))

        bonus = max(0, TIME_BONUS_BASE - int(self.level_time)) * TIME_BONUS_RATE
        rows = [
            ("Time", format_time(self.level_time)),
            ("Love tokens", f"{self.tokens_here} / {self.level.token_total}"),
            ("Token points", str(self.tokens_here * TOKEN_POINTS)),
            ("Time bonus", str(bonus)),
            ("Best time", format_time(self.save.best_time(self.level.name))),
        ]
        y = 270
        for label, value in rows:
            c.create_text(300, y, text=label, anchor="w", fill="#8A6A80",
                          font=(FONT, 13), tags=("ui",))
            c.create_text(700, y, text=value, anchor="e", fill=INK,
                          font=(FONT, 13, "bold"), tags=("ui",))
            y += 32

        c.create_line(300, 262, 700, 262, fill="#EFE0EA", tags=("ui",))

        pulse = 0.5 + 0.5 * math.sin(self.anim_t * 3.4)
        nxt = ("the castle" if self.level_index + 1 >= len(self.levels) - 1
               else self.levels[self.level_index + 1].name)
        c.create_text(SCREEN_W / 2, 436,
                      text=f"PRESS  ENTER  -  next: {nxt}",
                      fill=lerp_colour("#B0557E", "#FF5C8A", pulse),
                      font=(FONT, 15, "bold"), tags=("ui",))

    def render_gameover(self):
        c = self.canvas
        c.delete("all")
        self.gradient("#3B2B44", "#5A3B52")
        art.rounded_rect(c, 250, 160, 750, 420, 24, "#FFF6F8",
                         outline="#E8C7D6", width=3, tags=("ui",))
        c.create_text(SCREEN_W / 2, 212, text="OUT OF HEARTS",
                      fill="#C0456B", font=(FONT, 28, "bold"), tags=("ui",))
        art.draw_heart(c, SCREEN_W / 2, 262, 16, fill=HEART_EMPTY, tags=("ui",))
        c.create_text(SCREEN_W / 2, 310,
                      text="Even the long way round needs a second try.",
                      fill="#8A6A80", font=(FONT, 13), tags=("ui",))
        pulse = 0.5 + 0.5 * math.sin(self.anim_t * 3.4)
        c.create_text(SCREEN_W / 2, 360, text="PRESS  R  TO  RETRY",
                      fill=lerp_colour("#B0557E", "#FF5C8A", pulse),
                      font=(FONT, 17, "bold"), tags=("ui",))
        c.create_text(SCREEN_W / 2, 394, text="ESC  -  title screen",
                      fill="#B7A4BC", font=(FONT, 11), tags=("ui",))

    # -- the finale --------------------------------------------------------
    def update_ending(self, dt):
        self.cut_t += dt
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive][-400:]

        if self.cut_t > 13.0:
            self.firework_timer -= dt
            if self.firework_timer <= 0:
                self.firework_timer = 0.9
                self.spawn_firework(random.uniform(120, SCREEN_W - 120),
                                    random.uniform(90, 300), 2)

    def render_ending(self):
        c = self.canvas
        c.delete("all")
        t = self.cut_t

        # --- a warm hall inside the castle
        self.gradient("#2E2340", "#6B3F55")
        # arched window with a moon
        c.create_oval(390, 40, 610, 260, fill="#3B2E52", outline="#8A6A80",
                      width=3)
        c.create_oval(430, 80, 570, 220, fill="#20203C", outline="")
        c.create_oval(470, 96, 546, 172, fill="#FFEFC4", outline="")
        for i in range(14):
            sx = 440 + (i * 37) % 130
            sy = 100 + (i * 53) % 110
            c.create_oval(sx, sy, sx + 3, sy + 3, fill="#FFF6D0", outline="")

        # candles with a little brass holder
        for x in (250, 750):
            c.create_rectangle(x - 16, 408, x + 16, 430, fill="#8A6A34",
                               outline="")
            c.create_rectangle(x - 7, 300, x + 7, 410, fill="#F2E3C8",
                               outline="")
            flick = 3 + math.sin(self.anim_t * 9 + x) * 2
            c.create_oval(x - flick, 284 - flick, x + flick, 302,
                          fill="#FFD166", outline="")
            c.create_oval(x - 2, 290, x + 2, 298, fill="#FFF3C4", outline="")

        # floor + a strip of red carpet
        c.create_rectangle(0, 430, SCREEN_W, SCREEN_H, fill="#3A2A44",
                           outline="")
        c.create_rectangle(0, 430, SCREEN_W, 438, fill="#55395F", outline="")
        c.create_rectangle(150, 430, 850, 442, fill="#8E3550", outline="")

        # --- the two of them
        walk_done = min(1.0, t / 2.6)
        boy_x = 200 + walk_done * 345
        phase = t * 11 if walk_done < 1.0 else 0.0
        art.draw_girl(c, 672, 434, 3.4, facing=-1,
                      phase=math.sin(self.anim_t * 2) * 0.4, tags=("ui",))
        art.draw_boy(c, boy_x, 434, 3.4, facing=1, phase=phase, tags=("ui",))

        # hearts rising in the space between them
        if t > 2.6:
            for i in range(6):
                p = (t - 2.6) * 0.5 + i * 0.42
                hy = 424 - (p * 55) % 230
                hx = 612 + math.sin(p * 2.2 + i) * 20
                size = 6 + (i % 3) * 3
                if t > 2.6 + i * 0.35:
                    art.draw_heart(c, hx, hy, size, fill="#FF7FA5", tags=("ui",))

        # confetti
        for p in self.particles:
            if p.shape == "circle":
                c.create_oval(p.x, p.y, p.x + p.size, p.y + p.size,
                              fill=p.colour, outline="", tags=("ui",))
            else:
                c.create_rectangle(p.x, p.y, p.x + p.size, p.y + p.size,
                                   fill=p.colour, outline="", tags=("ui",))

        if t > 15.0:
            self.render_the_end()
            return

        # --- dialogue box
        art.rounded_rect(c, 70, 452, 930, 540, 18, "#1E1628",
                         outline="#C9A227", width=2, tags=("ui",))
        lines = STORY["ending"]
        shown = int(max(0, t - 2.8) // 2.0)
        shown = min(shown, len(lines) - 1)
        if t >= 2.8:
            text = lines[shown]
            is_question = text.strip().startswith('"Will')
            c.create_text(SCREEN_W / 2, 488, text=text,
                          fill="#FFE9A8" if is_question else "#F6E9F2",
                          font=(FONT, 18 if is_question else 15, "bold"),
                          width=820, justify="center", tags=("ui",))
            # little progress dots
            for i in range(len(lines)):
                col = "#FFD166" if i <= shown else "#4B3F5E"
                c.create_oval(470 + i * 12, 524, 476 + i * 12, 530,
                              fill=col, outline="", tags=("ui",))

    def render_the_end(self):
        """The final card - drawn on top of the frozen ballroom."""
        c = self.canvas
        c.create_rectangle(0, 0, SCREEN_W, SCREEN_H, fill="#1B1424",
                           outline="", stipple="gray50", tags=("ui",))
        art.rounded_rect(c, 250, 110, 750, 450, 26, "#241A30",
                         outline="#C9A227", width=3, tags=("ui",))
        art.draw_heart(c, SCREEN_W / 2, 168, 26, fill="#FF6B8B", tags=("ui",))
        c.create_text(SCREEN_W / 2, 236, text="THE  END",
                      fill="#FFF3F7", font=(FONT, 44, "bold"), tags=("ui",))
        c.create_text(SCREEN_W / 2, 288,
                      text=f"{PLAYER_NAME}  &  {PARTNER_NAME}",
                      fill="#FFC2D6", font=(FONT, 20, "bold"), tags=("ui",))
        c.create_line(330, 316, 670, 316, fill="#5A4470", tags=("ui",))
        c.create_text(SCREEN_W / 2, 342,
                      text=f"Total time  {format_time(self.run_time)}"
                           f"        Love tokens  {self.run_tokens}",
                      fill="#C9B8D2", font=(FONT, 13), tags=("ui",))
        pulse = 0.5 + 0.5 * math.sin(self.anim_t * 3.4)
        c.create_text(SCREEN_W / 2, 406, text="PRESS  ENTER",
                      fill=lerp_colour("#B0557E", "#FF8FB0", pulse),
                      font=(FONT, 16, "bold"), tags=("ui",))

    def render_credits(self):
        c = self.canvas
        c.delete("all")
        self.gradient("#1F1830", "#3A2A48")

        y = 56
        for i, line in enumerate(STORY["credits"]):
            if not line:
                y += 8
                continue
            size = 24 if i == 0 else 12
            colour = "#FFD166" if i == 0 else "#D8C9E0"
            c.create_text(SCREEN_W / 2, y, text=line, fill=colour,
                          font=(FONT, size, "bold" if i == 0 else "normal"),
                          tags=("ui",))
            y += 34 if i == 0 else 20

        # run summary
        art.rounded_rect(c, 260, 250, 740, 344, 16, "#2A2038",
                         outline="#5A4470", width=2, tags=("ui",))
        c.create_text(SCREEN_W / 2, 270, text="RUN SUMMARY", fill="#C9A227",
                      font=(FONT, 10, "bold"), tags=("ui",))
        c.create_text(320, 300, text="Total time", anchor="w",
                      fill="#B9A6C6", font=(FONT, 12), tags=("ui",))
        c.create_text(680, 300, text=format_time(self.run_time), anchor="e",
                      fill="#FFFFFF", font=(FONT, 12, "bold"), tags=("ui",))
        c.create_text(320, 326, text="Love tokens", anchor="w",
                      fill="#B9A6C6", font=(FONT, 12), tags=("ui",))
        c.create_text(680, 326, text=str(self.run_tokens), anchor="e",
                      fill="#FFFFFF", font=(FONT, 12, "bold"), tags=("ui",))

        # leaderboard (kept in order by the hand-written insertion sort)
        c.create_text(SCREEN_W / 2, 366, text="FASTEST RUNS", fill="#C9A227",
                      font=(FONT, 10, "bold"), tags=("ui",))
        board = self.save.leaderboard[:LEADERBOARD_SIZE]
        if not board:
            c.create_text(SCREEN_W / 2, 392, text="no runs recorded yet",
                          fill="#8A7A98", font=(FONT, 10), tags=("ui",))
        for i, rec in enumerate(board):
            text = (f"{i + 1}.   {rec['name']}    {format_time(rec['time'])}"
                    f"    {rec['tokens']} tokens")
            c.create_text(SCREEN_W / 2, 392 + i * 21, text=text,
                          fill="#FFE9A8" if i == 0 else "#A995B6",
                          font=(FONT, 11, "bold" if i == 0 else "normal"),
                          tags=("ui",))

        pulse = 0.5 + 0.5 * math.sin(self.anim_t * 3.4)
        c.create_text(SCREEN_W / 2, 532, text="PRESS  ENTER  -  BACK TO TITLE",
                      fill=lerp_colour("#8A6A98", "#FFB3CC", pulse),
                      font=(FONT, 11, "bold"), tags=("ui",))

    # -------------------------------------------------------------- selftest
    def smoke_test(self):
        """Headless run through every state - used during development."""
        try:
            self.root.withdraw()
            self.start_game()
            self.render()
            self.begin_play()
            assert self.canvas.find_withtag("static"), \
                "the level was not redrawn after the intro card"
            self.render()
            self.keys = {"right"}
            for _ in range(240):
                self.update(STEP)
                self.render()
            self.keys = {"right", "space"}
            for _ in range(60):
                self.update(STEP)
                self.render()
            self.state = "paused"
            self.render()
            self.canvas.delete("ui")
            self.state = "play"
            self.render()
            assert not self.canvas.find_withtag("ui"), \
                "the pause card was left on screen after resuming"
            for index in (1, 2):
                self.load_level(index)
                self.begin_play()
                for _ in range(90):
                    self.update(STEP)
                    self.render()
            self.state = "levelclear"
            self.render()
            self.state = "gameover"
            self.render()
            self.enter_ending()
            for _ in range(120):
                self.update(STEP)
                self.render()
            self.cut_t = 15.5
            self.render()
            self.enter_credits()
            self.render()
            self.enter_title()
            self.render()
            print("SMOKE OK - all states rendered")
        finally:
            self.running = False
            self.root.destroy()
