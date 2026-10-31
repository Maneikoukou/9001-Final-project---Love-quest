"""
Automated checks for the parts of Love Quest that do not need a window.

Run with:
    python3 tests/test_logic.py

The GUI itself is checked separately with:
    python3 main.py --smoke
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.entities import Coin, MovingPlatform, Player, Slime
from game.levels import all_levels
from game.save_system import SaveData, SaveSystem, sort_records
from game.settings import (PLAYER_H, PLAYER_W, SCREEN_H, SCREEN_W, STEP,
                           TILE)


# --------------------------------------------------------------------------
#  helpers
# --------------------------------------------------------------------------
def solid_at(solids, x, y):
    for (sx, sy, sw, sh) in solids:
        if sx <= x <= sx + sw and sy <= y <= sy + sh:
            return True
    return False


def simulate_jump(player, solids, seconds=0.9):
    """Hold jump from standstill and return the peak height gained."""
    start_y = player.y
    player.request_jump()
    peak = 0.0
    steps = int(seconds / STEP)
    for _ in range(steps):
        player.update(STEP, solids, False, False, True)
        peak = max(peak, start_y - player.y)
    return peak


# --------------------------------------------------------------------------
#  tests
# --------------------------------------------------------------------------
def test_inheritance():
    """Every game object must share the Entity base class."""
    from game.entities import Entity
    for cls in (Player, Slime, Coin, MovingPlatform):
        assert issubclass(cls, Entity), f"{cls.__name__} must inherit Entity"
    player = Player(0, 0)
    assert player.rect == (0.0, 0.0, PLAYER_W, PLAYER_H)
    print("ok  inheritance and AABB geometry")


def test_player_lands_on_ground():
    ground = [(0, 400, 2000, 160)]
    player = Player(100, 200)
    for _ in range(120):
        player.update(STEP, ground, False, False, False)
    assert player.on_ground, "player never landed"
    assert abs(player.y + PLAYER_H - 400) < 0.5, f"resting y={player.y}"
    print("ok  gravity + landing")


def test_jump_height_is_three_tiles():
    ground = [(0, 480, 2000, 80)]
    player = Player(100, 480 - PLAYER_H)
    player.update(STEP, ground, False, False, False)   # settle
    peak = simulate_jump(player, ground)
    tiles = peak / TILE
    assert 2.7 <= tiles <= 3.6, f"jump height {tiles:.2f} tiles"
    print(f"ok  jump height {peak:.0f}px = {tiles:.2f} tiles")


def test_horizontal_reach():
    """A running jump should clear a 3-tile gap."""
    ground = [(0, 480, 400, 80), (520, 480, 800, 80)]
    player = Player(300, 480 - PLAYER_H)
    player.update(STEP, ground, False, True, False)
    start_x = player.x
    player.request_jump()
    for _ in range(int(0.7 / STEP)):
        player.update(STEP, ground, False, True, True)
    travelled = player.x - start_x
    assert travelled > 3 * TILE, f"only cleared {travelled:.0f}px"
    print(f"ok  running jump covers {travelled:.0f}px "
          f"({travelled / TILE:.1f} tiles)")


def test_levels_are_sane():
    levels = all_levels()
    assert len(levels) == 3
    for lv in levels:
        assert lv.door_rect, f"{lv.name} has no goal door"
        assert lv.token_total >= 8, f"{lv.name} has too few tokens"
        dx, dy, dw, dh = lv.door_rect
        assert 0 < dx < lv.width - dw, f"{lv.name} door outside the level"
        assert dy + dh <= SCREEN_H, f"{lv.name} door below the floor"

        # the spawn point must not be inside a wall
        px, py = lv.start_pos
        assert not solid_at(lv.solids, px + PLAYER_W / 2, py + PLAYER_H / 2), \
            f"{lv.name} spawns inside a solid"

        # every solid must be inside the level
        for (sx, sy, sw, sh) in lv.solids:
            assert sx >= 0 and sx + sw <= lv.width + 1, f"{lv.name} solid off-map"

        # no gap between ground segments may exceed a running jump
        edges = sorted((sx, sx + sw) for (sx, sy, sw, sh) in lv.solids
                       if sh > 100 and sy <= 12 * TILE + 1)
        for (a_start, a_end), (b_start, b_end) in zip(edges, edges[1:]):
            gap = b_start - a_end
            assert gap <= 3.2 * TILE, f"{lv.name} gap of {gap:.0f}px is too wide"
    print(f"ok  {len(levels)} levels validated")


def test_spawn_returns_fresh_objects():
    lv = all_levels()[0]
    coins_a, slimes_a, movers_a, cps_a = lv.spawn()
    coins_b, slimes_b, movers_b, cps_b = lv.spawn()
    assert len(coins_a) == lv.token_total
    assert coins_a[0] is not coins_b[0], "spawn must build new instances"
    print(f"ok  level spawn ({len(coins_a)} tokens, {len(slimes_a)} slimes)")


def test_save_roundtrip():
    data = SaveData()
    assert data.record_time("Sunlit Meadow", 61.4) is True
    assert data.record_time("Sunlit Meadow", 70.0) is False    # slower
    assert data.record_time("Sunlit Meadow", 55.2) is True     # new PB
    assert data.best_time("Sunlit Meadow") == 55.2

    data.leaderboard = [
        {"name": "A", "time": 90.0, "tokens": 10, "date": "2026-01-01"},
        {"name": "B", "time": 42.0, "tokens": 20, "date": "2026-01-01"},
        {"name": "C", "time": 61.0, "tokens": 30, "date": "2026-01-01"},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "save.json")
        assert SaveSystem.save(data, path) is True
        loaded = SaveSystem.load(path)
        assert loaded.best_time("Sunlit Meadow") == 55.2
        assert [r["name"] for r in loaded.leaderboard] == ["B", "C", "A"]
        assert loaded.leaderboard[0]["time"] == 42.0
    print("ok  save / load roundtrip + insertion-sorted leaderboard")


def test_corrupt_save_is_survivable():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "save.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{ this is not json ]")
        data = SaveSystem.load(path)
        assert data.best_times == {} and data.leaderboard == []
        # a missing file must behave the same way
        missing = SaveSystem.load(os.path.join(tmp, "nope.json"))
        assert missing.total_tokens == 0
    print("ok  corrupt / missing save files fall back to defaults")


def test_insertion_sort():
    records = [{"time": t} for t in (5.0, 1.0, 9.5, 3.2, 1.0, 7.7)]
    ordered = [r["time"] for r in sort_records(records)]
    assert ordered == sorted(ordered), ordered
    assert len(ordered) == 6
    print("ok  insertion sort orders records")


def test_entity_behaviour():
    slime = Slime(100, 400, 60, 160)
    for _ in range(200):
        slime.update(STEP)
    assert 60 <= slime.x <= 160 - slime.w, "slime escaped its patrol"
    slime.stomp()
    assert not slime.alive

    mover = MovingPlatform(0, 0, 80, 16, "x", 50, 2.0)
    xs = set()
    for _ in range(120):
        mover.update(STEP)
        xs.add(round(mover.x))
    assert len(xs) > 10, "moving platform is not moving"

    player = Player(0, 0)
    assert player.hurt(100) is True
    assert player.hearts == 2
    assert player.hurt(100) is True          # invulnerable, no extra damage
    assert player.hearts == 2
    print("ok  slime patrol, moving platform and damage rules")


def main():
    tests = [
        test_inheritance,
        test_player_lands_on_ground,
        test_jump_height_is_three_tiles,
        test_horizontal_reach,
        test_levels_are_sane,
        test_spawn_returns_fresh_objects,
        test_save_roundtrip,
        test_corrupt_save_is_survivable,
        test_insertion_sort,
        test_entity_behaviour,
    ]
    for test in tests:
        test()
    print(f"\nAll {len(tests)} logic checks passed.")


if __name__ == "__main__":
    main()
