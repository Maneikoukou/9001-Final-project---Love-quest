# Love Quest: A Castle for Two

A side-scrolling platform game written in Python. Play as Batiao, cross three hand-built lands, gather love tokens, and reach Daisy at the castle. The ending is an animated proposal scene.

## Requirements

The game uses **Tkinter to create a graphical window**. Tkinter is part of Python's standard library on many installations, so there is no third-party package to install, but this is still a GUI application. On some Linux installations, Tkinter must be installed separately (`python3-tk`).

## Running the game

```bash
python3 main.py
```

On macOS, you can also double-click `Play Love Quest.command`. Use Python 3.8 or newer with Tkinter available. The game draws its characters, scenery, and effects with Canvas shapes; it uses no image, audio, or video assets and no networking.

## Controls

| Key | Action |
| --- | --- |
| `←` `→` or `A` `D` | Move |
| `Space` / `W` / `↑` | Jump — hold longer to jump higher |
| `Esc` | Pause; `Q` in the pause menu returns to the title |
| `R` | Retry after running out of hearts |
| `Enter` | Start, advance dialogue, or continue from a level-clear screen |

## What is in the game

- Three levels with distinct scenery and pacing: *The Open Steppe*, *The Dusk Crossing*, and *The Castle of Us*.
- Batiao's cartoon character wears a black Mongolian *deel*; the first two levels use colours inspired by the grassland reference photo.
- Platform movement includes acceleration, friction, variable jump height, coyote time, and jump buffering.
- Patrolling slimes, spikes, pits, moving platforms, tokens, and checkpoints.
- Hearts, per-level timer, personal bests, score, and a saved top-five leaderboard.
- A proposal cutscene with dialogue, recursive confetti, and credits.

## Project layout

```
Love_Quest_Batiao_Daisy/
├── main.py                 entry point
├── game/                   settings, entities, levels, persistence, art, app
├── tests/test_logic.py     10 automated logic checks
├── tools/                  development helpers
├── assets/                 cover image and in-game screenshots
```

## Personalising it

Names and story text are in `game/settings.py`. The current names are **Batiao** and **Daisy**. The `THEMES` dictionary controls the level palettes.

## Development checks

The project includes these checks:

```bash
python3 tests/test_logic.py
python3 main.py --smoke
python3 tools/autoplay.py
```

The smoke test creates a Tkinter window, so it also needs a graphical desktop session.

## Design notes

### Architecture

The code is split into a small entry point and a `game/` package, so each
module has a single job:

| Module | Responsibility |
| --- | --- |
| `main.py` | Starts Tkinter, builds the app, handles the `--smoke` flag |
| `game/settings.py` | All tunable constants, the colour palettes and the story text |
| `game/entities.py` | The `Entity` base class and every moving object |
| `game/levels.py` | The `Level` builder API and the three campaign levels |
| `game/save_system.py` | JSON persistence, defensive loading and the leaderboard sort |
| `game/art.py` | Procedural drawing helpers (no image files) |
| `game/app.py` | Window, game loop, state machine, HUD and cutscenes |

Every moving object inherits from one `Entity` base class, which owns an
axis-aligned bounding box (AABB) and simple velocity state:

```
Entity
 ├── Player            hero: input, physics, damage
 ├── Slime             patrolling enemy
 ├── Coin              collectable love token
 ├── MovingPlatform    oscillating platform that carries the player
 ├── Particle          confetti / dust / sparkles
 └── Checkpoint        moves the respawn point
```

Levels are declared with a readable builder API instead of raw pixel
coordinates, e.g. `level.ground(0, 9, 12)` or `level.coin_arc(35, 9, 5)`, so a
platform can be nudged by one tile without disturbing the rest of the layout.

Rendering is split in two. The **static** layer (sky, ground, platforms,
scenery) is drawn once per level and then slid sideways as the camera moves,
while the **dynamic** layer (player, enemies, tokens, particles) is redrawn
every frame. This keeps the frame rate steady on modest hardware.

### Physics

The simulation runs on a fixed 1/60-second timestep, so behaviour is identical
no matter how fast the screen refreshes. Movement uses acceleration and
friction with a top speed; gravity pulls the player down to a terminal velocity
that stops thin platforms from being tunnelled through. Three small timing
helpers give the controls a modern feel:

- **Variable jump height** — releasing the jump key early clamps upward
  velocity, so a tap gives a short hop and a hold gives a full jump.
- **Coyote time** — a short grace window after walking off a ledge during
  which a jump still works.
- **Jump buffering** — a jump pressed just before landing is remembered and
  fires the moment the player touches down.

Collision is resolved one axis at a time (X first, then Y) against a list of
solid rectangles, which cleanly separates "hit a wall" from "landed on a
floor". A moving platform reports how far it travelled each frame, so a player
standing on it is carried along.

### Game state machine

A single state value drives what the player sees, with an explicit `enter_*`
method for each transition:

```
title ──▶ intro ──▶ play ◀──▶ paused
                     │
                     ├──▶ levelclear ──▶ intro (next level)
                     ├──▶ gameover ───▶ play (retry)
                     └──▶ ending ──▶ credits ──▶ title
```

Keeping the states explicit means the menus, dialogue and finale never fight
over input, and each screen can redraw itself independently.

### Techniques used

Beyond the core loop, the project demonstrates inheritance, JSON file I/O with
defensive exception handling, a hand-written insertion sort for the leaderboard,
recursion (the firework confetti burst), and the state machine described above.

