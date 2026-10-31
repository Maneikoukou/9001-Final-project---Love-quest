"""
Development helper (not part of the submitted game)
===================================================

A very simple bot that plays each level with "hold right + jump when
something is in the way".  It is used to prove that every level can actually
be finished - if the bot can walk to the castle door, a human definitely can.

    python3 tools/autoplay.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.entities import Player
from game.levels import all_levels
from game.settings import PLAYER_H, PLAYER_W, SCREEN_H, STEP


def solid_at(solids, x, y):
    for (sx, sy, sw, sh) in solids:
        if sx <= x <= sx + sw and sy <= y <= sy + sh:
            return True
    return False


def hazard_ahead(hazards, player, reach=46):
    probe = (player.right, player.bottom - 12, reach, 24)
    for (hx, hy, hw, hh) in hazards:
        if (probe[0] < hx + hw and probe[0] + probe[2] > hx
                and probe[1] < hy + hh and probe[1] + probe[3] > hy):
            return True
    return False


def landing_ahead(solids, player):
    """Is there something to land on just in front of us (or below us)?"""
    for step in range(40, 200, 12):
        x = player.right + step
        for (sx, sy, sw, sh) in solids:
            if sx <= x <= sx + sw and -150 <= sy - player.bottom <= 200:
                return True
    return False


def play(level, max_seconds=240.0, verbose=False):
    player = Player(*level.start_pos)
    coins, slimes, movers, cps = level.spawn()
    player.hearts = 99                      # ignore combat, test traversal
    seconds = 0.0
    stuck_at = None
    best_x = player.x

    while seconds < max_seconds:
        solids = list(level.solids)
        for mover in movers:
            mover.update(STEP)
            solids.append(mover.rect)

        right = True
        jump = False
        if player.on_ground:
            wall = solid_at(solids, player.right + 6, player.bottom - 26)
            gap = not solid_at(solids, player.right + 30, player.bottom + 14)
            if wall or hazard_ahead(level.hazards, player):
                jump = True
            elif gap:
                if landing_ahead(solids, player):
                    jump = True
                else:
                    right = False           # wait for the moving platform
        if jump:
            player.request_jump()           # same call the keyboard handler makes
        player.update(STEP, solids, False, right, True)

        if player.y > SCREEN_H + 120:
            return False, seconds, f"fell into a pit at x={player.x:.0f}"

        if level.door_rect and player.overlaps(level.door_rect):
            return True, seconds, "reached the door"

        # detect being stuck
        if player.x > best_x + 2:
            best_x = player.x
            stuck_at = seconds
        elif stuck_at is not None and seconds - stuck_at > 8:
            return False, seconds, f"stuck at x={player.x:.0f}"

        seconds += STEP

    return False, seconds, f"timed out at x={player.x:.0f}"


def main():
    ok = True
    for level in all_levels():
        success, seconds, reason = play(level)
        flag = "PASS" if success else "FAIL"
        print(f"[{flag}] {level.name:<20} {seconds:6.1f}s  {reason}")
        ok = ok and success
    print("\nAll levels reachable." if ok else "\nSome levels need tuning.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
